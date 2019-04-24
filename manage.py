#!/usr/bin/env python
import click
import shlex

from flask.cli import FlaskGroup

from peterboy import main
from subprocess import Popen, PIPE


def create_app():
    return main.app


@click.group(cls=FlaskGroup, create_app=create_app)
def cli():
    """Management script for the Wiki application."""


@cli.command()
def syncdb():
    """데이터베이스 초기화 작업"""

    from peterboy.database import init_db
    init_db()

    click.echo(click.style("데이터베이스 생성이 완료되었습니다.", fg='blue'))


@cli.command()
def upload():
    """구글에 데이터 업로드 하기"""
    proc = Popen(shlex.split("gcloud app deploy --project=peterboy --version=20190424t110524"), stdout=PIPE)
    proc.communicate()


@cli.command()
def calc_line():
    import os
    import stat

    wc = 0
    size = 0

    def file_wc(path):
        with open(path, 'rb') as file_obj:
            return len(file_obj.readlines())

    def file_size(path):
        return os.stat(path)[stat.ST_SIZE]

    for root, dirs, files in os.walk("."):
        for entry in files:
            last_path = os.path.join(root, entry)
            if 'peterboy' in last_path:
                if 'peterboy/static' in last_path:
                    continue

                wc += file_wc(last_path)
                size += file_size(last_path)
            elif 'migration' in last_path:
                continue

    wc += len(open('.gitignore', 'r').readlines())
    wc += len(open('manage.py', 'r').readlines())

    click.echo('현재까지 {0:#,} 줄을 작성하셨습니다. 분발하셔야 하겠어요'.format(wc))
    click.echo('현재까지 {0:#,} 용량을 작성하셨습니다. 분발하셔야 하겠어요'.format(size))


if __name__ == '__main__':
    cli.main()
