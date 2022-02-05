import logging
import os

import sqlalchemy
import sqlalchemy.exc
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

if __database_url := os.getenv("DATABASE_URL"):
    # Raise ImportError is driver is not installed,
    # other errors are due to an incorrect url syntax
    engine = sqlalchemy.create_engine(__database_url)
else:
    # At this point, no url was specified for a remote database, let's create one
    logger.warning(
        "You have not specified an DATABASE_URL environment variable, "
        "a local SQLLite database will be created. "
        "Please, restart the script if this is not the desired behavior "
    )
    engine = sqlalchemy.create_engine("sqlite:///:memory:")


def test_connection():
    """
    Tests if the connection to the database.
    """
    try:
        engine.connect()  # test connection
    except (
        sqlalchemy.exc.ProgrammingError,
        sqlalchemy.exc.InterfaceError,
        sqlalchemy.exc.TimeoutError,
    ) as err:
        logger.fatal(f"Can't connect to the database with this URL: {__database_url}")
        raise err
    else:
        *_, database_name = __database_url.rpartition("/")
        logger.info(
            f"A connection to the database {database_name} "
            f"was successful established"
        )
    return True


def execute(stmt):
    """
    Creates a Session to execute the given statement.
    """
    with Session(engine, autocommit=True) as session:
        try:
            # https://docs.sqlalchemy.org/en/14/errors.html#error-lkrp
            result = session.execute(stmt, execution_options={"prebuffer_rows": True})
        except sqlalchemy.exc.DBAPIError as err:
            # https://docs.sqlalchemy.org/en/13/core/exceptions.html
            logger.error(
                f"The following statement execution has failed: \n"
                f"{err.statement} \n"
                f"Full error stack: {err}"
            )
        else:
            return result
    return None


def get_dialect() -> str:
    return engine.dialect.name
