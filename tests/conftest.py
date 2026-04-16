import pytest
from sqlalchemy import create_engine
from unittest.mock import patch

from src.api.db import Base


@pytest.fixture()
def db_engine():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with patch("src.api.db._get_engine", return_value=engine):
        yield engine
