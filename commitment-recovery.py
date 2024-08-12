import os
import sys
import git
import argparse
import subprocess

from datetime import datetime
from utils import to_wsl, run


def main(def_args=None):
    if def_args is None:
        def_args = sys.argv[1:]
    args = arguments(def_args)

    # Convert the source path to WSL format if necessary
    source_path = to_wsl(args.source)

    # Get repository commit history.
    try:
        repo = git.Repo(source_path)
    except git.exc.NoSuchPathError:
        print(f"Source repository path '{source_path}' does not exist.")
        return None

    commits_list = []
    for commit in repo.iter_commits():
        commits_list.append({
            'date': commit.authored_datetime,
            'message': commit.message.strip(),
            'user_email': commit.author.email,
            'hash': commit.hexsha
        })

    # Get Filter emails.
    email_filters = []
    if args.email_filters is not None:
        email_filters = args.email_filters.split(',')
    else:
        try:
            email_filter = subprocess.check_output(['git', 'config', 'user.email']).decode('utf-8').strip()
            email_filters.append(email_filter)
            print("Email filter is: {}".format(email_filters))
        except subprocess.CalledProcessError as e:
            print("Error getting git config:", e)
            return None

    # Create target repository.

    if args.target is not None:
        target_directory = args.target
    else:
        current_date = datetime.now()
        target_directory = source_path + '-commitment-recovery-' + current_date.strftime('%Y-%m-%d-%H-%M-%S')

    os.mkdir(target_directory)
    os.chdir(target_directory)

    run(['git', 'init', '-b', 'main'])

    # Recover history.

    for commit in reversed(commits_list):
        if args.hide_message:
            message = commit['date'].strftime('%Y/%m/%d %H:%M:%S')
        else:
            message = (commit['date'].strftime('%Y/%m/%d (%H:%M:%S): ') + commit['message'] +
                       '\nsource: ' + commit['hash'])

        if commit['user_email'] in email_filters:
            git_commit(commit['date'], message)


def git_commit(date, message):
    with open(os.path.join(os.getcwd(), 'README.md'), 'a') as file:
        file.write(message + '\n\n')
    run(['git', 'add', '.'])
    run(['git', 'commit', '-m', '%s' % message, '--date', date.strftime('"%Y-%m-%d %H:%M:%S"')])

def arguments(argsval):
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--source',
                        type=str,
                        required=True,
                        help="""Path of the directory of the source repository.""")
    parser.add_argument('-t', '--target',
                        type=str,
                        required=False,
                        help="""Path where to create the target repository. If none, target repository will be created
                        with the name of the source repository and the -commitment-recovery-{Date} suffix.""")
    parser.add_argument('-ef', '--email_filters',
                        type=str,
                        required=False,
                        help="""Comma-separated list of emails. Only commits signed with the given emails will be considered.
                        If none, it uses the current git config user email.""")
    parser.add_argument('-hm', '--hide_message',
                        action='store_true',
                        help="""Does not copy the commit message to the target repository.""")
    return parser.parse_args(argsval)


if __name__ == "__main__":
    main()