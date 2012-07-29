import os
import fabric
from fabric.api import env, local, sudo, cd, prefix

env.hosts = ['praveen@173.255.241.59']
env.master_repo = 'git+ssh://git@github.com/pgollakota/zosimus.git'
env.activate = 'source /work/virtualenvs/zosimus/bin/activate'
env.project_root = '/home/praveen/cows/zosimus'


def run(cmd):
    with cd(env.project_root):
        with prefix(env.activate):
            fabric.api.run(cmd)


def push():
    local('git push %(master_repo)s' % env)
    run('git pull -u %(master_repo)s' % env)


def build_docs():
    with prefix('export DJANGO_SETTINGS_MODULE=zosimus.settings'):
        run('cd docs && make html')


def install_requirements():
    run('pip install -r requirements.txt -q')


def upgrade_db():
    run('cd zosimus && python manage.py syncdb')


def deploy_static():
    run('cd zosimus && python manage.py collectstatic -v0 --noinput')


def restart_webserver():
    sudo('supervisorctl restart nginx')
    sudo('supervisorctl restart chartit')


def deploy():
    push()
    install_requirements()
    upgrade_db()
    deploy_static()
    restart_webserver()