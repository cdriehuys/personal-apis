from io import StringIO
import os

from django.template import Context
from django.template import Engine

from fabric.api import cd, env, local, prefix, put, run, sudo, task

required_packages = (
    'git',
    'libpq-dev',
    'postgresql', 'postgresql-contrib',
    'nginx',
    'python3-dev', 'python3-pip',
    'ufw',
)


def get_local_settings():
    """
    Retrieve settings for this deployment.

    Most aspects of the deployment can be modified in this function.

    Returns:
        dict: A settings dictionary.
    """
    settings = {}

    settings['base_dir'] = os.path.dirname(os.path.abspath(__file__))

    settings['project_name'] = 'personal-apis'
    settings['project_package'] = 'personal_apis'
    settings['project_url'] = 'https://github.com/cdriehuys/personal-apis'

    settings['remote_user'] = 'chathan'
    settings['remote_group'] = 'www-data'

    settings['remote_home'] = os.path.join('/', 'home', settings['remote_user'])
    settings['remote_project_dir'] = os.path.join(settings['remote_home'], settings['project_name'])
    settings['project_env'] = os.path.join(settings['remote_project_dir'], 'env')

    # Django Settings
    settings['django_local_settings'] = os.path.join(settings['remote_project_dir'], settings['project_package'],
                                                     settings['project_package'], 'local_settings.py')
    settings['django_static_root'] = os.path.join('/', 'var', 'www', env.host, 'static')

    # Gunicorn Settings
    settings['gunicorn_application'] = '{package}.wsgi:application'.format(package=settings['project_package'])
    settings['gunicorn_bin'] = os.path.join(settings['project_env'], 'bin', 'gunicorn')
    settings['gunicorn_proxy'] = 'unix:{path}'.format(path=os.path.join(settings['remote_project_dir'],
                                                                        settings['project_package'],
                                                                        '{package}.sock'.format(
                                                                            package=settings['project_package'])))
    settings['gunicorn_service'] = os.path.join('/', 'etc', 'systemd', 'system', 'gunicorn.service')
    settings['gunicorn_workers'] = '3'
    settings['gunicorn_working_dir'] = os.path.join(settings['remote_project_dir'], settings['project_package'])

    # Nginx Settings
    settings['nginx_conf'] = os.path.join('/', 'etc', 'nginx', 'sites-available', env.host)
    settings['nginx_enabled_dir'] = os.path.join('/', 'etc', 'nginx', 'sites-enabled')

    # Virtualenv Settings
    settings['venv_activate'] = os.path.join(settings['project_env'], 'bin', 'activate')

    return settings


@task
def deploy():
    """
    Deploy codebase to a remote machine.
    """
    prepare_local()
    prepare_remote()
    update_remote()


@task
def prepare_local():
    """
    Prepare the local machine for deployment.
    """
    # From http://stackoverflow.com/a/11958481/3762084
    env.current_branch = local(
        'git rev-parse --symbolic-full-name --abbrev-ref HEAD',
        capture=True)

    local('git push')


@task
def prepare_remote():
    """
    Prepare the remote machine for deployment.

    This includes installing and configuring the required packages.
    """
    settings = get_local_settings()

    sudo('apt-get update -y')

    to_install = ' '.join(required_packages)
    sudo('apt-get install -y {packages}'.format(packages=to_install))

    _configure_gunicorn()
    _configure_nginx()

    # Make sure static dir exists
    sudo('if ! test -d {static_dir}; then mkdir -p {static_dir}; fi'.format(static_dir=settings['django_static_root']))
    sudo('chown -R {user}:{group} {static_dir}'.format(
        group=settings['remote_group'],
        static_dir=settings['django_static_root'],
        user=settings['remote_user']))


@task
def update_remote():
    """
    Update the code on the remote machine.
    """
    settings = get_local_settings()

    with cd(settings['remote_home']):
        run('if ! test -d {project_name}; then git clone {project_url}; fi'.format(
            project_name=settings['project_name'], project_url=settings['project_url']))

    with cd(settings['remote_project_dir']):
        run('git pull && git checkout {branch} && git pull'.format(
            branch=env.current_branch))

    _configure_env()

    # Nuke existing local settings
    run('rm -f {local_settings}'.format(local_settings=settings['django_local_settings']))

    # Upload new local settings
    context = {
        'domain_name': env.host,
        'static_root': settings['django_static_root'],
    }
    _upload_template('config_templates/local_settings.template', settings['django_local_settings'], context)

    # Run migrations and collect static files
    with cd(settings['remote_project_dir']), prefix('source {activate}'.format(activate=settings['venv_activate'])):
        manage_cmd = '{package}/manage.py'.format(package=settings['project_package'])

        def management_cmd(cmd):
            run('{mng} {cmd}'.format(cmd=cmd, mng=manage_cmd))

        management_cmd('migrate')
        management_cmd('collectstatic --noinput')

    sudo('systemctl restart gunicorn')


def _configure_env():
    """
    Configure the remote project's virtualenv.
    """
    settings = get_local_settings()

    run('if ! test -d {env}; then virtualenv --python=python3 {env}; fi'.format(env=settings['project_env']))

    with prefix('source {activate}'.format(activate=settings['venv_activate'])):
        req = os.path.join(settings['remote_project_dir'], 'requirements.txt')

        run('pip install -r {req}'.format(req=req))


def _configure_gunicorn():
    """
    Configure gunicorn to serve django application.
    """
    settings = get_local_settings()

    context = {
        'group': settings['remote_group'],
        'gunicorn': settings['gunicorn_bin'],
        'gunicorn_workers': settings['gunicorn_workers'],
        'proxy_address': settings['gunicorn_proxy'],
        'user': settings['remote_user'],
        'working_directory': settings['gunicorn_working_dir'],
        'wsgi_application': settings['gunicorn_application'],
    }

    _upload_template('config_templates/gunicorn-service.template', settings['gunicorn_service'], context, use_sudo=True)

    sudo('systemctl daemon-reload')
    sudo('systemctl start gunicorn')
    sudo('systemctl enable gunicorn')


def _configure_nginx():
    """
    Configure nginx to serve application.
    """
    settings = get_local_settings()

    context = {
        'domain_name': env.host,
        'proxy_address': settings['gunicorn_proxy'],
        'static_root': settings['django_static_root'],
    }

    _upload_template('config_templates/nginx-conf.template', settings['nginx_conf'], context, use_sudo=True)
    sudo('ln -fs {conf} {enabled_dir}'.format(conf=settings['nginx_conf'], enabled_dir=settings['nginx_enabled_dir']))

    # Test and restart
    sudo('nginx -t')
    sudo('systemctl restart nginx')


def _upload_template(template_name, dest_path, context=None, **kwargs):
    """
    Upload a template with the given context data.
    """
    context = context or {}

    with open(template_name) as f:
        template = Engine().from_string(f.read())

    handle = StringIO()
    handle.write(template.render(Context(context)))
    handle.seek(0)

    put(handle, dest_path, **kwargs)
