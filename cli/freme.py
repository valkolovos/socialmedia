#!/usr/bin/env python3

import click
import functools
import json
import requests
import os

def is_logged_in(func):
    @functools.wraps(func)
    def logged_in_wrapper(*args, **kwargs):
        try:
            with open('/tmp/.freme') as f:
                session_data = json.loads(f.read())
            resp = requests.get(
                f'{session_data["protocol"]}://{session_data["host"]}/validate-session',
                cookies=dict(session=session_data['session'])
            )
            if resp.status_code == 200:
                ctx = click.get_current_context()
                ctx.ensure_object(dict)
                ctx.obj['session_data'] = session_data
                ctx.obj['current_user'] = json.loads(resp.content)['email']
                return func(*args, **kwargs)
        except (FileNotFoundError, KeyError):
            pass
        click.echo('Not logged in')
    return logged_in_wrapper

@click.group()
def freme():
    ''' CLI to interact with Social Media project. For help with specific commands, run freme.py [command] --help '''
    pass

@freme.group()
def message():
    ''' Message options '''
    pass

@message.command()
@is_logged_in
def get():
    ''' doc string for get '''
    print('getting messages')
    session_data = click.get_current_context().obj['session_data']
    resp = requests.get(
        f'{session_data["protocol"]}://{session_data["host"]}/get-messages',
        cookies=dict(session=session_data['session'])
    )
    if resp.status_code == 200:
        messages = json.loads(resp.content)
        click.echo(messages)
    else:
        click.echo(f'failed to get messages {resp.status_code}')

@message.command()
@click.argument('message')
@is_logged_in
def post(message):
    ''' doc string for post '''
    print('posting message')
    session_data = click.get_current_context().obj['session_data']
    resp = requests.post(
        f'{session_data["protocol"]}://{session_data["host"]}/create-message',
        data={'message': message},
        cookies=dict(session=session_data['session'])
    )
    if resp.status_code == 200:
        click.echo(resp.content)
    else:
        click.echo(f'failed to post message {resp.status_code}')

@message.command()
@click.argument('connection_id')
@click.argument('message_id')
@click.argument('comment')
@is_logged_in
def comment(connection_id, message_id, comment):
    session_data = click.get_current_context().obj['session_data']
    resp = requests.post(
        f'{session_data["protocol"]}://{session_data["host"]}/add-comment/{message_id}',
        data={'comment': comment, 'connectionId': connection_id},
        cookies=dict(session=session_data['session'])
    )
    if resp.status_code == 200:
        click.echo(resp.content)
    else:
        click.echo(f'failed to post message {resp.status_code}')

@freme.group()
def connection():
    pass

@connection.command(name='list')
@is_logged_in
def list_connections():
    session_data = click.get_current_context().obj['session_data']
    resp = requests.get(
        f'{session_data["protocol"]}://{session_data["host"]}/get-connection-info',
        cookies=dict(session=session_data['session'])
    )
    if resp.status_code == 200:
        connection_data = json.loads(resp.content)
        pending_connections = []
        existing_connections = []
        for conn in connection_data:
            if conn['status'] == 'pending':
                pending_connections.append(conn)
            else:
                existing_connections.append(conn)
        click.echo('Pending Connections')
        for pending in pending_connections:
            click.echo(f"({pending['id']}) {pending['handle']}@{pending['host']} - {pending['display_name']}")
        click.echo('\nExisting Connections')
        for existing in existing_connections:
            new_message_notification = ''
            if existing['unread_message_count']:
                new_message_notification = f' ({existing["unread_message_count"]})'
            click.echo(f"({existing['id']}) {existing['handle']}@{existing['host']}{new_message_notification}")
    else:
        click.echo(f'failed to post message {resp.status_code}')

@connection.command()
@click.argument('handle')
@click.argument('host')
@is_logged_in
def request(handle, host):
    session_data = click.get_current_context().obj['session_data']
    resp = requests.post(
        f'{session_data["protocol"]}://{session_data["host"]}/request-connection',
        cookies=dict(session=session_data['session']),
        data={'host': host, 'handle': handle}
    )
    if resp.status_code == 200:
        click.echo('connection request succeeded')
    else:
        click.echo(f'connection request failed {resp.status_code}')

@connection.command()
@click.argument('connection_id')
@is_logged_in
def acknowledge(connection_id):
    session_data = click.get_current_context().obj['session_data']
    resp = requests.post(
        f'{session_data["protocol"]}://{session_data["host"]}/manage-connection',
        cookies=dict(session=session_data['session']),
        json={'action': 'connect', 'connection_id': connection_id}
    )
    if resp.status_code == 200:
        click.echo('connection acknowledged')
    else:
        click.echo(f'connection acknowledge failed {resp.status_code}')

@connection.command()
@click.argument('connection_id')
@is_logged_in
def messages(connection_id):
    session_data = click.get_current_context().obj['session_data']
    resp = requests.get(
        f'{session_data["protocol"]}://{session_data["host"]}//get-connection-messages/{connection_id}',
        cookies=dict(session=session_data['session']),
    )
    if resp.status_code == 200:
        click.echo(resp.content)
    else:
        click.echo(f'unable to retrieve messages {resp.status_code}')
        click.echo(resp.content)

@freme.command()
@click.option('--host', prompt='Host to connect to')
@click.option('--email', prompt='Your email')
@click.option('--display-name', prompt='Name to display to others')
@click.option('--handle', prompt='Short name to reference you by (think username)')
@click.password_option(confirmation_prompt=False)
@click.option('--protocol', default='https')
def signup(host, email, display_name, handle, password, protocol):
    resp = requests.post(
        f'{protocol}://{host}/signup',
        data={
            'email': email, 'name': display_name, 'handle': handle,
            'password': password
        }
    )
    if resp.status_code == 200:
        session_data = {
            'host': host,
            'protocol': protocol,
            'session': resp.cookies['session']
        }
        with open('/tmp/.freme', 'w') as f:
            f.write(json.dumps(session_data))
        click.echo('Signup successful and user is logged in')
    else:
        click.echo(f'Signup failed {resp.status_code}')

@freme.command()
@click.argument('host')
@click.argument('email')
@click.password_option(confirmation_prompt=False)
@click.option('--protocol', default='https')
def login(host, email, password, protocol):
    resp = requests.post(
        f'{protocol}://{host}/login-api',
        data={'email': email, 'password': password}
    )
    if resp.status_code == 200:
        session_data = {
            'host': host,
            'protocol': protocol,
            'session': resp.cookies['session']
        }
        with open('/tmp/.freme', 'w') as f:
            f.write(json.dumps(session_data))
        click.echo('login successful')
    else:
        click.echo(f'login failed {resp.status_code}')
        click.echo(resp.content)

@freme.command()
@is_logged_in
def logout():
    session_data = click.get_current_context().obj['session_data']
    resp = requests.get(
        f'{session_data["protocol"]}://{session_data["host"]}/sign-out',
        cookies=dict(session=session_data['session'])
    )
    if resp.status_code == 200:
        os.remove('/tmp/.freme')
        click.echo('logged out')
    else:
        click.echo(f'failed to log out {resp.status_code}')

@freme.command()
@is_logged_in
def whoami():
    click.echo(click.get_current_context().obj['current_user'])

if __name__ == '__main__':
    freme()
