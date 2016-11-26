from io import StringIO
import os

from django.template import Context
from django.template import Engine

from fabric.api import cd, env, local, prefix, put, run, sudo, task

required_packages = (
    'git',
    'letsencrypt',
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

    settings['email'] = 'cdriehuys@gmail.com'

    settings['remote_user'] = 'chathan'
    settings['remote_group'] = 'www-data'

    settings['remote_home'] = os.path.join('/', 'home', settings['remote_user'])
    settings['remote_project_dir'] = os.path.join(settings['remote_home'], settings['project_name'])
    settings['project_env'] = os.path.join(settings['remote_project_dir'], 'env')

    settings['web_root'] = os.path.join('/', 'var', 'www', env.host)

    # Django Settings
    settings['django_local_settings'] = os.path.join(settings['remote_project_dir'], settings['project_package'],
                                                     settings['project_package'], 'local_settings.py')
    settings['django_secure_settings'] = os.path.join(settings['remote_project_dir'], settings['project_package'],
                                                      settings['project_package'], 'secure_settings.py')
    settings['django_static_root'] = os.path.join(settings['web_root'], 'static')

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

    # Letsencrypt Settings
    settings['letsencrypt_cert_dir'] = os.path.join('/', 'etc', 'letsencrypt', 'live', env.host)

    settings['letsencrypt_bin'] = os.path.join('/', 'usr', 'bin', 'letsencrypt')
    settings['letsencrypt_cert'] = os.path.join(settings['letsencrypt_cert_dir'], 'fullchain.pem')
    settings['letsencrypt_dh_cert'] = os.path.join('/', 'etc', 'ssl', 'certs', 'dhparam.pem')
    settings['letsencrypt_dh_cmd'] = 'openssl dhparam -out {dh_cert} 2048'.format(
        dh_cert=settings['letsencrypt_dh_cert'])
    settings['letsencrypt_key'] = os.path.join(settings['letsencrypt_cert_dir'], 'privkey.pem')
    settings['letsencrypt_log'] = os.path.join('/', 'var', 'log', 'le-renew.log')
    settings['letsencrypt_web_root'] = os.path.join(settings['web_root'], 'html')

    # Nginx Settings
    settings['nginx_conf'] = os.path.join('/', 'etc', 'nginx', 'sites-available', env.host)
    settings['nginx_enabled_dir'] = os.path.join('/', 'etc', 'nginx', 'sites-enabled')
    settings['nginx_snippet_dir'] = os.path.join('/', 'etc', 'nginx', 'snippets')
    settings['nginx_ssl_domain_snippet'] = os.path.join(settings['nginx_snippet_dir'], 'ssl-{domain}.conf'.format(
        domain=env.host))
    settings['nginx_ssl_params_snippet'] = os.path.join(settings['nginx_snippet_dir'], 'ssl-params.conf')

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
    _configure_ssl()

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
        'package_name': settings['project_package'],
        'static_root': settings['django_static_root'],
    }
    _upload_template('config_templates/local_settings.template', settings['django_local_settings'], context)

    # Make sure secure settings are present
    exists = run('if test -f {secure_file}; then echo exists; fi'.format(
        secure_file=settings['django_secure_settings']))

    if exists != 'exists':
        run('touch {0}'.format(settings['django_secure_settings']))
        run('echo "SECRET_KEY = \'{key}\'" > {settings}'.format(
            key=input('Django secret key: '),
            settings=settings['django_secure_settings']))

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
        'web_root': settings['letsencrypt_web_root'],
    }

    _upload_template('config_templates/nginx-conf-basic.template', settings['nginx_conf'], context, use_sudo=True)
    sudo('ln -fs {conf} {enabled_dir}'.format(conf=settings['nginx_conf'], enabled_dir=settings['nginx_enabled_dir']))

    # Test and restart
    sudo('nginx -t')
    sudo('systemctl restart nginx')


def _configure_ssl():
    """
    Configure SSL on the remote machine.

    Ensures the letsencrypt certificate is set up and renewed.
    """
    settings = get_local_settings()

    configured = sudo('if test -d {cert_dir}; then echo exists; fi'.format(cert_dir=settings['letsencrypt_cert_dir']))

    if configured == 'exists':
        _renew_ssl()
    else:
        _set_up_ssl()

    # Configure NGINX to use SSL
    context = {
        'domain_name': env.host,
        'proxy_address': settings['gunicorn_proxy'],
        'ssl_domain_snippet': settings['nginx_ssl_domain_snippet'],
        'ssl_params_snippet': settings['nginx_ssl_params_snippet'],
        'static_root': settings['django_static_root'],
    }
    _upload_template('config_templates/nginx-conf.template',
                     settings['nginx_conf'],
                     context,
                     use_sudo=True)

    context = {
        'cert_path': settings['letsencrypt_cert'],
        'key_path': settings['letsencrypt_key'],
    }
    _upload_template('config_templates/ssl-domain.template',
                     settings['nginx_ssl_domain_snippet'],
                     context,
                     use_sudo=True)

    context = {
        'dh_cert': settings['letsencrypt_dh_cert'],
    }
    _upload_template('config_templates/ssl-params.template',
                     settings['nginx_ssl_params_snippet'],
                     context,
                     use_sudo=True)

    # Test and restart NGINX
    sudo('nginx -t')
    sudo('systemctl restart nginx')

    # Configure auto renewals
    with cd('/tmp'):
        run('echo "30 2 * * 1 {letsencrypt} renew >> {log}" > newcron'.format(
            letsencrypt=settings['letsencrypt_bin'],
            log=settings['letsencrypt_log']))
        run('echo "35 2 * * 1 /bin/systemctl reload nginx" >> newcron')
        run('crontab newcron')
        run('rm newcron')


def _renew_ssl():
    """
    Attempt to renew the SSL certs on the server.
    """
    sudo('letsencrypt renew')


def _set_up_ssl():
    """
    Set up a new SSL cert on the server.
    """
    settings = get_local_settings()

    sudo('if ! test -d {web_root}; then mkdir -p {web_root}; fi'.format(web_root=settings['letsencrypt_web_root']))
    sudo('chown -R {user}:{group} {web_root}'.format(
        group=settings['remote_group'],
        user=settings['remote_user'],
        web_root=settings['letsencrypt_web_root']))

    cmd = ' '.join([
        'letsencrypt certonly',
        '-a webroot',
        '--agree-tos',
        '-d {0}'.format(env.host),
        '--email {email}'.format(email=settings['email']),
        '--webroot-path={web_root}'.format(web_root=settings['letsencrypt_web_root']),
    ])
    sudo(cmd)

    # Create Diffie-Hellman group
    sudo(settings['letsencrypt_dh_cmd'])


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
