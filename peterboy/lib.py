from peterboy.models import Client

NOTE_DATETIMESTAMP = "%Y-%m-%dT%H:%M:%S.%f+09:00"


def new_client(user_id):
    return Client(
        user_id=user_id,
        client_id='anyone',
        client_secret='anyone',
        default_redirect_uri='oob',
    )
