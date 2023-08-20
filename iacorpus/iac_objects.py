import sys
import importlib
from importlib.util import find_spec

from sqlalchemy.exc import OperationalError

import iacorpus.datasets.generic
from iacorpus.datasets.generic.dataset import SQLConnection, Dataset


def load_dataset(name: str, **kwargs) -> Dataset:
    """Returns a dataset.

    This dynamically connects to the database and prepares a Dataset object.
    It first tries iacorpus.datasets.<name>
    and if that doesn't exist it uses iacorpus.datasets.generic
    Various keyword args provide database connection details (included below).

    Args:
        name: the name of the dataset to load

    Keyword Args:
        database_name: the database to connect to (default is name)
        connection_details_filename: filename with connection credentials
            host, port, password, etc.
            see data/sql_auth.json.bak
            If a filename is not specified, this will also try
            the IAC_CONNECTION_DETAILS environment variable.
            Note that this is not especially secure.
        connection_details_configuration_name: which connection information
            in connection_details_filename should be used
            (defaults to whatever the file specifies is the "default_configuration")
        host: database host (defaults to localhost)
        port: database port (defaults to 3306)
        username: database username (defaults to iacuser)
        password: database password (defaults to no password)
        dbapi: the underlying connection method (defaults to "mysql+mysqldb")
            see sqlalchemy documentation
    """
    assert name.replace('_', '').isalnum(), 'invalid dataset name: %s' % name
    spec = find_spec("iacorpus.datasets."+name)
    if spec is not None:
        dataset_module = importlib.import_module(spec.name)
    else:
        dataset_module = iacorpus.datasets.generic
    kwargs['name'] = name
    try:
        dataset = dataset_module.load_dataset(**kwargs)
    except OperationalError as exception:
        if 'Access denied for user' in exception.args[0]:
            print('Failed to connect to the database!',
                  'Check your user permissions and your spelling:', name, '\n\n', file=sys.stderr)
        raise
    return dataset


def load_connection(name: str, **kwargs) -> SQLConnection:
    """Returns just the connection to the database.

    Notes:
        Still builds the dataset.
    """
    dataset = load_dataset(name, **kwargs)
    return dataset.connection
