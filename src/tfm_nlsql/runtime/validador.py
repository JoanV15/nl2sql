"""Validador de política sobre el AST (D-19). No busca palabras clave."""

from __future__ import annotations

import sqlglot
from sqlglot import exp

LIMITE_FILAS = 1000
TABLAS_PERMITIDAS = frozenset(
    {"obt_pedidos", "obt_lineas_pedido", "obt_vendedores", "obt_embudo_web"}
)
FUNCIONES_TABLA_PERMITIDAS: frozenset[str] = frozenset()

_SENTENCIAS_OK = (exp.Select, exp.Union, exp.Except, exp.Intersect, exp.With)
_DDL_DML = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Create,
    exp.Drop,
    exp.Alter,
    exp.Command,
    exp.Copy,
    exp.Grant,
    exp.Set,
    exp.Use,
    exp.Pragma,
    exp.Analyze,
    exp.TruncateTable,
)


class ErrorValidacion(Exception):
    def __init__(self, motivo: str):
        self.motivo = motivo
        super().__init__(motivo)


def inyectar_limite(sql: str) -> str:
    """Reescribe ANTES de validar: la cadena resultante es la que se ejecuta."""
    try:
        ast = sqlglot.parse_one(sql, dialect="duckdb")
    except sqlglot.errors.ParseError as e:
        raise ErrorValidacion(f"SQL no analizable: {e}") from e
    if ast is None:
        raise ErrorValidacion("SQL vacío")
    _aplicar_limite(ast)
    return ast.sql(dialect="duckdb")


def _aplicar_limite(ast: exp.Expression) -> None:
    raiz = ast.this if isinstance(ast, exp.With) else ast
    if isinstance(raiz, exp.Union):
        if raiz.args.get("limit") is None:
            raiz.set("limit", exp.Limit(expression=exp.Literal.number(LIMITE_FILAS)))
        return
    if isinstance(raiz, exp.Select):
        if raiz.args.get("limit") is None:
            raiz.limit(LIMITE_FILAS, copy=False)
            return
        n = _valor_limite(raiz.args["limit"])
        if n is not None and n > LIMITE_FILAS:
            raiz.limit(LIMITE_FILAS, copy=False)


def _valor_limite(nodo: exp.Expression) -> int | None:
    expr = nodo.args.get("expression") if isinstance(nodo, exp.Limit) else nodo
    if isinstance(expr, exp.Literal) and expr.is_number:
        try:
            return int(expr.this)
        except (TypeError, ValueError):
            return None
    return None


def validar_politica(sql: str, columnas_por_tabla: dict[str, frozenset[str]]) -> None:
    try:
        sentencias = sqlglot.parse(sql, dialect="duckdb")
    except sqlglot.errors.ParseError as e:
        raise ErrorValidacion(f"SQL no analizable: {e}") from e
    if len(sentencias) != 1 or sentencias[0] is None:
        raise ErrorValidacion("solo se admite una sentencia")
    ast = sentencias[0]
    if isinstance(ast, _DDL_DML) or not isinstance(ast, _SENTENCIAS_OK):
        raise ErrorValidacion("solo se permiten SELECT y WITH")
    derivados = _nombres_derivados(ast)
    for nodo in ast.walk():
        if isinstance(nodo, _DDL_DML):
            raise ErrorValidacion("solo se permiten SELECT y WITH")
        if isinstance(nodo, exp.Table):
            _validar_tabla(nodo, derivados)
    _validar_sin_cartesiano(ast)
    _validar_columnas(ast, columnas_por_tabla, derivados)


def _validar_sin_cartesiano(ast: exp.Expression) -> None:
    """Rechaza el cruce sin condición: `FROM a, b`, `CROSS JOIN` y `JOIN` pelado.

    Una generación truncada por D-35 deja el `ON` fuera y el cruce resultante
    devuelve una cifra plausible pero mil veces menor (traza 149: 0,003 % de
    clientes recurrentes frente al 3,12 % real). El binding de DuckDB no lo ve:
    el SQL es válido.

    Detecta la condición ausente, no una tautología como `ON 1 = 1`. Si el
    modelo llegase a escribirla, haría falta comprobar que la condición liga
    columnas de ambos lados.
    """
    for join in ast.find_all(exp.Join):
        if join.args.get("on") is not None or join.args.get("using"):
            continue
        lado = join.this
        nombre = lado.name or lado.alias or type(lado).__name__
        raise ErrorValidacion(
            f"producto cartesiano: el cruce con {nombre} no declara condición "
            "de enlace. Usa una subconsulta escalar o un JOIN con ON."
        )


def _nombres_derivados(ast: exp.Expression) -> set[str]:
    nombres: set[str] = set()
    for cte in ast.find_all(exp.CTE):
        if cte.alias:
            nombres.add(cte.alias.lower())
    for sub in ast.find_all(exp.Subquery):
        if sub.alias:
            nombres.add(sub.alias.lower())
    # `FROM totales AS t` deja el alias como único nombre con el que se
    # cualifican las columnas: sin esto, `t.columna` se toma por una tabla
    # ajena a la lista blanca y se rechaza SQL legítimo del Nivel 3.
    for tabla in ast.find_all(exp.Table):
        if tabla.name and tabla.name.lower() in nombres and tabla.alias:
            nombres.add(tabla.alias.lower())
    return nombres


def _validar_tabla(nodo: exp.Table, derivados: set[str]) -> None:
    this = nodo.this
    if isinstance(this, exp.Func | exp.Anonymous):
        nombre = (this.name or type(this).__name__).lower()
        if nombre not in FUNCIONES_TABLA_PERMITIDAS:
            raise ErrorValidacion(f"función de tabla no permitida: {nombre}")
        return
    nombre = (nodo.name or "").lower()
    if not nombre:
        raise ErrorValidacion("tabla sin nombre")
    if nombre in derivados or nombre in TABLAS_PERMITIDAS:
        return
    raise ErrorValidacion(f"tabla no permitida: {nodo.name}")


def tablas_gold_citadas(sql: str) -> list[str]:
    """Tablas de la lista blanca que aparecen en el SQL, en orden de aparición."""
    if not sql or not sql.strip():
        return []
    try:
        ast = sqlglot.parse_one(sql, dialect="duckdb")
    except sqlglot.errors.ParseError:
        return []
    if ast is None:
        return []
    derivados = _nombres_derivados(ast)
    vistas: list[str] = []
    for tabla in ast.find_all(exp.Table):
        nombre = (tabla.name or "").lower()
        if (
            nombre in TABLAS_PERMITIDAS
            and nombre not in derivados
            and nombre not in vistas
        ):
            vistas.append(nombre)
    return vistas


def _alias_fisicas(ast: exp.Expression, derivados: set[str]) -> dict[str, str]:
    alias: dict[str, str] = {}
    for tabla in ast.find_all(exp.Table):
        if not tabla.name:
            continue
        real = tabla.name.lower()
        if real in derivados:
            continue
        alias[real] = real
        if tabla.alias:
            alias[tabla.alias.lower()] = real
    return alias


def _alias_select(ast: exp.Expression) -> set[str]:
    nombres: set[str] = set()
    for sel in ast.find_all(exp.Select):
        for e in sel.expressions:
            if e.alias:
                nombres.add(e.alias.lower())
    return nombres


def _validar_columnas(
    ast: exp.Expression,
    columnas_por_tabla: dict[str, frozenset[str]],
    derivados: set[str],
) -> None:
    alias = _alias_fisicas(ast, derivados)
    usadas = set(alias.values())
    permitidas: set[str] = set()
    for t in usadas:
        permitidas |= {c.lower() for c in columnas_por_tabla.get(t, frozenset())}
    aliases_salida = _alias_select(ast) | derivados
    for col in ast.find_all(exp.Column):
        if col.is_star:
            continue
        nombre = col.name
        if not nombre:
            continue
        clave = nombre.lower()
        tabla_ref = col.table.lower() if col.table else None
        if tabla_ref:
            if tabla_ref in derivados:
                continue
            real = alias.get(tabla_ref)
            if real is None:
                raise ErrorValidacion(f"tabla no permitida: {col.table}")
            cols = {c.lower() for c in columnas_por_tabla.get(real, frozenset())}
            if clave not in cols:
                raise ErrorValidacion(f"columna no permitida: {real}.{nombre}")
            continue
        if clave in permitidas or clave in aliases_salida:
            continue
        raise ErrorValidacion(f"columna no permitida: {nombre}")
