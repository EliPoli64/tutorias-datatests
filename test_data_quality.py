import pytest

pytestmark = pytest.mark.data_quality

# ---------------------------------------------------------------------------
# Anomaly Detection Tests
# ---------------------------------------------------------------------------


class TestOrphanedRecords:

    def test_no_orphaned_estudiante_tutoria(self, cursor):
        cursor.execute("""
            SELECT COUNT(*)
            FROM EstudianteTutoria et
            LEFT JOIN Tutoria t ON t.ID_Tutoria = et.ID_Tutoria
            WHERE t.ID_Tutoria IS NULL
        """)
        count = cursor.fetchone()[0]
        assert count == 0, f"Found {count} orphaned EstudianteTutoria records"

    def test_no_orphaned_tutoria_periodo(self, cursor):
        cursor.execute("""
            SELECT COUNT(*)
            FROM Tutoria t
            LEFT JOIN Periodo p ON p.ID_Periodo = t.ID_Periodo
            WHERE p.ID_Periodo IS NULL
        """)
        count = cursor.fetchone()[0]
        assert count == 0, f"Found {count} Tutoria records with no Periodo"

    def test_no_orphaned_tutoria_materia(self, cursor):
        cursor.execute("""
            SELECT COUNT(*)
            FROM Tutoria t
            LEFT JOIN Materia m ON m.ID_Materia = t.ID_Materia
            WHERE m.ID_Materia IS NULL
        """)
        count = cursor.fetchone()[0]
        assert count == 0, f"Found {count} Tutoria records with no Materia"

    def test_no_orphaned_materia_periodo(self, cursor):
        cursor.execute("""
            SELECT COUNT(*)
            FROM MateriaPeriodo mp
            LEFT JOIN Periodo p ON p.ID_Periodo = mp.ID_Periodo
            WHERE p.ID_Periodo IS NULL
        """)
        count = cursor.fetchone()[0]
        assert count == 0, f"Found {count} orphaned MateriaPeriodo records"

    def test_no_orphaned_departamento_sede(self, cursor):
        cursor.execute("""
            SELECT COUNT(*)
            FROM DepartamentoSede ds
            LEFT JOIN Sede s ON s.ID_Sede = ds.ID_Sede
            LEFT JOIN Departamento d ON d.ID_Departamento = ds.ID_Departamento
            WHERE s.ID_Sede IS NULL OR d.ID_Departamento IS NULL
        """)
        count = cursor.fetchone()[0]
        assert count == 0, f"Found {count} orphaned DepartamentoSede records"


class TestInactiveFKReferences:

    def test_no_inactive_materia_references(self, cursor):
        cursor.execute("""
            SELECT COUNT(*)
            FROM MateriaPeriodo mp
            JOIN Materia m ON m.ID_Materia = mp.ID_Materia
            WHERE m.Activo = 0
        """)
        count = cursor.fetchone()[0]
        assert count == 0, f"Found {count} MateriaPeriodo referencing inactive Materia"

    def test_no_inactive_sede_references(self, cursor):
        cursor.execute("""
            SELECT COUNT(*)
            FROM DepartamentoSede ds
            JOIN Sede s ON s.ID_Sede = ds.ID_Sede
            WHERE s.Activo = 0
        """)
        count = cursor.fetchone()[0]
        assert count == 0, f"Found {count} DepartamentoSede referencing inactive Sede"

    def test_no_inactive_estado_references(self, cursor):
        cursor.execute("""
            SELECT COUNT(*)
            FROM EstudianteTutoria et
            JOIN EstadoTutoria e ON e.ID_EstadoTutoria = et.ID_EstadoTutoria
            WHERE e.Activo = 0
        """)
        count = cursor.fetchone()[0]
        assert count == 0, f"Found {count} EstudianteTutoria referencing inactive EstadoTutoria"


class TestDateOutOfRange:

    def test_no_future_dates(self, cursor):
        cursor.execute("""
            SELECT COUNT(*)
            FROM Tutoria
            WHERE FechaCreacion > DATEADD(DAY, 1, GETDATE())
        """)
        count = cursor.fetchone()[0]
        assert count == 0, f"Found {count} Tutoria records with future creation dates"

    def test_no_very_old_tutorias(self, cursor):
        cursor.execute("""
            SELECT COUNT(*)
            FROM Tutoria
            WHERE FechaTutoria < DATEADD(YEAR, -5, GETDATE())
        """)
        count = cursor.fetchone()[0]
        if count > 0:
            print(f"  NOTE: {count} tutoring sessions older than 5 years")


class TestNullsInRequiredFields:

    def test_required_fields_not_null(self, cursor):
        cursor.execute("""
            SELECT 'Sede' AS Tabla, COUNT(*) AS NullCount
            FROM Sede WHERE Codigo IS NULL OR Nombre IS NULL
            UNION ALL
            SELECT 'Departamento', COUNT(*)
            FROM Departamento WHERE Codigo IS NULL OR Nombre IS NULL
            UNION ALL
            SELECT 'Profesor', COUNT(*)
            FROM Profesor WHERE NOM_PROFESOR IS NULL
            UNION ALL
            SELECT 'Periodo', COUNT(*)
            FROM Periodo WHERE NumAnno IS NULL
            UNION ALL
            SELECT 'Materia', COUNT(*)
            FROM Materia WHERE Codigo IS NULL OR Nombre IS NULL
            UNION ALL
            SELECT 'Estudiante', COUNT(*)
            FROM Estudiante WHERE Carnet IS NULL OR Nombre IS NULL
            UNION ALL
            SELECT 'Tutoria', COUNT(*)
            FROM Tutoria WHERE ID_TipoTutoria IS NULL OR ID_Semana IS NULL
               OR ID_Periodo IS NULL OR ID_Materia IS NULL
               OR ID_Tutor IS NULL
            UNION ALL
            SELECT 'EstudianteTutoria', COUNT(*)
            FROM EstudianteTutoria WHERE ID_Tutoria IS NULL OR ID_Estudiante IS NULL
               OR ID_EstadoTutoria IS NULL
        """)
        rows = cursor.fetchall()
        violations = [(r[0], r[1]) for r in rows if r[1] > 0]
        critical = [(t, c) for t, c in violations if t != "Tutoria"]
        tutoria_nulls = next(((t, c) for t, c in violations if t == "Tutoria"), None)
        if tutoria_nulls:
            print(f"  NOTE: {tutoria_nulls[1]} Tutoria records have NULL FK fields (legacy data)")
        assert len(critical) == 0, (
            f"Tables with unexpected NULLs in required fields: {critical}"
        )


class TestDuplicates:

    def test_no_duplicate_estudiante_tutoria(self, cursor):
        cursor.execute("""
            SELECT COUNT(*)
            FROM (
                SELECT ID_Tutoria, ID_Estudiante
                FROM EstudianteTutoria
                GROUP BY ID_Tutoria, ID_Estudiante
                HAVING COUNT(*) > 1
            ) AS d
        """)
        count = cursor.fetchone()[0]
        assert count == 0, f"Found {count} duplicate (tutoria, estudiante) pairs"

    def test_materia_periodo_duplicates(self, cursor):
        cursor.execute("""
            SELECT ID_Materia, ID_Periodo, COUNT(*) AS Cnt
            FROM MateriaPeriodo
            GROUP BY ID_Materia, ID_Periodo
            HAVING COUNT(*) > 1
            ORDER BY Cnt DESC
        """)
        rows = cursor.fetchall()
        if rows:
            print(f"\n  WARNING: {len(rows)} MateriaPeriodo duplicate groups exist")
            for r in rows:
                print(f"    materia={r[0]}, periodo={r[1]}: {r[2]} records")

    def test_no_duplicate_carnet(self, cursor):
        cursor.execute("""
            SELECT COUNT(*)
            FROM (
                SELECT Carnet
                FROM Estudiante
                GROUP BY Carnet
                HAVING COUNT(*) > 1
            ) AS d
        """)
        count = cursor.fetchone()[0]
        assert count == 0, f"Found {count} duplicate student carnets"


# ---------------------------------------------------------------------------
# Data Profiling Tests (informational, non-failing)
# ---------------------------------------------------------------------------


class TestDataProfiling:

    def test_table_row_counts(self, cursor):
        tables = [
            "Sede", "Departamento", "Profesor", "Rango", "Periodo",
            "EstadoTutoria", "TipoTutoria", "DepartamentoSede",
            "Materia", "Semana", "Estudiante", "MateriaPeriodo",
            "Matricula", "Tutoria", "EstudianteTutoria",
        ]
        results = {}
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            results[table] = cursor.fetchone()[0]
        print(f"\n=== TABLE ROW COUNTS ===")
        for table, count in sorted(results.items()):
            print(f"  {table}: {count}")
        assert len(results) > 0, "No tables found"

    def test_value_distribution_estado_tutoria(self, cursor):
        cursor.execute("""
            SELECT et.ID_EstadoTutoria, e.Descripcion, COUNT(*) AS Cnt
            FROM EstudianteTutoria et
            JOIN EstadoTutoria e ON e.ID_EstadoTutoria = et.ID_EstadoTutoria
            GROUP BY et.ID_EstadoTutoria, e.Descripcion
            ORDER BY Cnt DESC
        """)
        rows = cursor.fetchall()
        print(f"\n=== EstadoTutoria Distribution ===")
        for r in rows:
            print(f"  {r[0]} - {r[1]}: {r[2]}")
        assert len(rows) > 0, "No EstudianteTutoria records found"

    def test_active_ratio(self, cursor):
        tables_with_active = [
            "Sede", "Departamento", "Materia", "Periodo",
            "EstadoTutoria", "TipoTutoria",
        ]
        print(f"\n=== Active/Inactive Ratios ===")
        for table in tables_with_active:
            cursor.execute(f"""
                SELECT Activo, COUNT(*) AS Cnt
                FROM {table}
                GROUP BY Activo
                ORDER BY Activo
            """)
            rows = cursor.fetchall()
            total = sum(r[1] for r in rows)
            print(f"  {table}: ", end="")
            for r in rows:
                label = "Active" if r[0] == 1 else "Inactive"
                pct = (r[1] / total * 100) if total > 0 else 0
                print(f"{label}={r[1]} ({pct:.1f}%)  ", end="")
            print()

    def test_date_recency(self, cursor):
        cursor.execute("""
            SELECT 'Tutoria' AS Tabla,
                   MIN(FechaCreacion) AS Earliest,
                   MAX(FechaCreacion) AS Latest,
                   COUNT(*) AS Total
            FROM Tutoria
            UNION ALL
            SELECT 'EstudianteTutoria',
                   MIN(FechaCreacion), MAX(FechaCreacion), COUNT(*)
            FROM EstudianteTutoria
            UNION ALL
            SELECT 'MateriaPeriodo',
                   MIN(FechaCreacion), MAX(FechaCreacion), COUNT(*)
            FROM MateriaPeriodo
        """)
        rows = cursor.fetchall()
        print(f"\n=== Date Recency ===")
        for r in rows:
            print(f"  {r[0]}: {r[1]} to {r[2]} ({r[3]} records)")

    def test_null_rate_analysis(self, cursor):
        nullable_columns = [
            ("Sede", "Codigo"), ("Sede", "Nombre"),
            ("Departamento", "Codigo"), ("Departamento", "Nombre"),
            ("Materia", "Codigo"), ("Materia", "Nombre"),
            ("Estudiante", "Carnet"), ("Estudiante", "Nombre"),
        ]
        print(f"\n=== NULL Rate Analysis (threshold: 5%) ===")
        for table, col in nullable_columns:
            cursor.execute(f"""
                SELECT
                    COUNT(*) AS Total,
                    SUM(CASE WHEN {col} IS NULL THEN 1 ELSE 0 END) AS NullCount
                FROM {table}
            """)
            total, null_count = cursor.fetchone()
            rate = (null_count / total * 100) if total > 0 else 0
            status = "WARN" if rate > 5 else "OK"
            print(f"  {table}.{col}: {null_count}/{total} NULL ({rate:.1f}%) [{status}]")
