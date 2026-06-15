import pytest
import pyodbc


@pytest.fixture(scope="session")
def cursor():
    conn = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=localhost\\SQLEXPRESS08;"
        "DATABASE=BDTutoriasDOPEntities;"
        "Trusted_Connection=yes;"
    )
    c = conn.cursor()
    yield c
    conn.close()
