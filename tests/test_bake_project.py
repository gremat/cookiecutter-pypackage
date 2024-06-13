"""Tests for cookiecutter-pypackage."""
import datetime
import importlib
import os
import shlex
import subprocess
import sys
from contextlib import contextmanager

import pytest  # pylint: disable=unused-import
from cookiecutter.utils import rmtree
from typer.testing import CliRunner


@contextmanager
def inside_dir(dirpath):
    """
    Execute code from inside the given directory
    :param dirpath: String, path of the directory the command is being run.
    """
    old_path = os.getcwd()
    try:
        os.chdir(dirpath)
        yield
    finally:
        os.chdir(old_path)


@contextmanager
def bake_in_temp_dir(cookies, *args, **kwargs):
    """
    Delete the temporal directory that is created when executing the tests
    :param cookies: pytest_cookies.Cookies,
        cookie to be baked and its temporal files will be removed
    """
    result = cookies.bake(*args, **kwargs)
    try:
        yield result
    finally:
        rmtree(str(result.project_path))


def run_inside_dir(command, dirpath):
    """
    Run a command from inside a given directory, returning the exit status
    :param command: Command that will be executed
    :param dirpath: String, path of the directory the command is being run.
    """
    commands: list[str] = command if isinstance(command, list) else [command]
    with inside_dir(dirpath):
        for cmd in commands:
            if (ret := subprocess.check_call(shlex.split(cmd))) != 0:
                return ret
        return 0


def check_output_inside_dir(command, dirpath):
    """Run a command from inside a given directory, returning the command output"""
    with inside_dir(dirpath):
        return subprocess.check_output(shlex.split(command))


def test_year_compute_in_license_file(cookies):
    with bake_in_temp_dir(cookies) as result:
        license_file_path = result.project_path.joinpath('LICENSE')
        now = datetime.datetime.now()
        assert str(now.year) in license_file_path.read_text()


def project_info(result) -> tuple[str, str]:
    """Get project dir and project_slug from baked cookies"""
    assert result.exception is None
    assert result.project_path.is_dir()

    project_path = str(result.project_path)
    project_slug = os.path.split(project_path)[-1]
    return project_path, project_slug


def test_bake_with_defaults(cookies):
    with bake_in_temp_dir(cookies) as result:
        assert result.project_path.is_dir()
        assert result.exit_code == 0
        assert result.exception is None

        found_toplevel_files = [f.stem for f in result.project_path.iterdir()]
        assert 'tests' in found_toplevel_files


def test_bake_and_run_tests(cookies):
    with bake_in_temp_dir(cookies) as result:
        assert result.project_path.is_dir()
        assert run_inside_dir(['python3 -m build', 'pytest'], str(result.project_path)) == 0
        print('test_bake_and_run_tests path', str(result.project_path))


def test_bake_with_apostrophe_and_run_tests(cookies):
    """Ensure that a `full_name` with apostrophes does not break the build"""
    with bake_in_temp_dir(
        cookies,
        extra_context={'full_name': "O'connor"}
    ) as result:
        assert result.project_path.is_dir()
        assert run_inside_dir(['python3 -m build', 'pytest'], str(result.project_path)) == 0


# def test_bake_and_run_travis_pypi_setup(cookies):
#     # given:
#     with bake_in_temp_dir(cookies) as result:
#         project_path = str(result.project_path)
#
#         # when:
#         travis_setup_cmd = ('python travis_pypi_setup.py'
#                             ' --repo audreyr/cookiecutter-pypackage'
#                             ' --password invalidpass')
#         run_inside_dir(travis_setup_cmd, project_path)
#         # then:
#         result_travis_config = yaml.load(
#             result.project_path.joinpath(".travis.yml").open()
#         )
#         min_size_of_encrypted_password = 50
#         assert len(
#             result_travis_config["deploy"]["password"]["secure"]
#         ) > min_size_of_encrypted_password


def test_make_help(cookies):
    with bake_in_temp_dir(cookies) as result:
        # The supplied Makefile does not support win32
        if sys.platform != 'win32':
            output = check_output_inside_dir(
                'make help',
                str(result.project_path)
            )
            assert b'run tests quickly with the default Python' in \
                output


def test_bake_selecting_license(cookies):
    license_strings = {
        'MIT license': 'MIT ',
        'BSD license': 'Redistributions of source code must retain the ' +
                       'above copyright notice, this',
        'ISC license': 'ISC License',
        'Apache Software License 2.0':
            'Licensed under the Apache License, Version 2.0',
        'GNU General Public License v3': 'GNU GENERAL PUBLIC LICENSE',
    }
    for lic_key, target_string in license_strings.items():
        with bake_in_temp_dir(
            cookies,
            extra_context={'open_source_license': lic_key}
        ) as result:
            assert target_string in result.project_path.joinpath('LICENSE').read_text()
            assert lic_key in result.project_path.joinpath('pyproject.toml').read_text()


def test_bake_not_open_source(cookies):
    with bake_in_temp_dir(
        cookies,
        extra_context={'open_source_license': 'Not open source'}
    ) as result:
        found_toplevel_files = [f.stem for f in result.project_path.iterdir()]
        assert 'LICENSE' not in found_toplevel_files
        assert 'License' not in result.project_path.joinpath('README.md').read_text()


def test_using_pytest(cookies):
    with bake_in_temp_dir(
        cookies,
        extra_context={'use_pytest': 'y'}
    ) as result:
        assert result.project_path.is_dir()
        test_file_path = result.project_path.joinpath(
            'tests/test_python_boilerplate.py'
        )
        assert 'import pytest' in test_file_path.read_text()
        # Test the new pytest target
        assert run_inside_dir('pytest', str(result.project_path)) == 0


# def test_project_with_hyphen_in_module_name(cookies):
#     result = cookies.bake(
#         extra_context={'project_name': 'something-with-a-dash'}
#     )
#     assert result.project_path is not None
#     project_path = str(result.project_path)
#
#     # when:
#     travis_setup_cmd = ('python travis_pypi_setup.py'
#                         ' --repo audreyr/cookiecutter-pypackage'
#                         ' --password invalidpass')
#     run_inside_dir(travis_setup_cmd, project_path)
#
#     # then:
#     result_travis_config = yaml.load(
#         open(os.path.join(project_path, ".travis.yml"))
#     )
#     assert "secure" in result_travis_config["deploy"]["password"],\
#         "missing password config in .travis.yml"


def test_bake_with_console_script_files(cookies):
    with bake_in_temp_dir(cookies) as result:
        toml_path = result.project_path.joinpath('pyproject.toml')
        with open(toml_path, 'r', encoding='utf-8') as toml_file:
            assert '[project.scripts]' in toml_file.read()


def test_bake_with_console_script_cli(cookies):
    with bake_in_temp_dir(cookies) as result:
        project_slug = result.context['project_slug']
        module_name = project_slug
        module_path = result.project_path.joinpath('src', project_slug, f'{project_slug}.py')
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cli)
        runner = CliRunner()
        noarg_result = runner.invoke(cli.app)
        assert noarg_result.exit_code == 0
        noarg_output = ' '.join(['This is', project_slug])
        assert noarg_output in noarg_result.output
        help_result = runner.invoke(cli.app, ['--help'])
        assert help_result.exit_code == 0
        assert 'Show this message' in help_result.output
