# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/00_core.ipynb.

# %% auto 0
__all__ = ['convertTypes', 'noop', 'identity', 'Table', 'View', 'custom_dir', 'Database']

# %% ../nbs/00_core.ipynb 3
@patch(as_prop=True)
def table_names(self: DuckDBPyConnection): 
    return [r[0] for r in db.sql(f"SELECT table_name FROM duckdb_tables() WHERE schema_name = current_schema()").fetchall()]
@patch(as_prop=True)
def view_names(self: DuckDBPyConnection): 
    return [r[0] for r in db.sql(f"SELECT view_name FROM duckdb_views() WHERE schema_name = current_schema() and internal = False").fetchall()]
@patch(as_prop=True)
def function_names(self: DuckDBPyConnection): 
    return [r[0] for r in db.sql(f"SELECT function_name FROM duckdb_functions() WHERE schema_name = current_schema() and internal=False").fetchall()]

# %% ../nbs/00_core.ipynb 6
@patch(as_prop=True) # alias for alias
def name(self:DuckDBPyRelation): return self.alias

@patch # use __getitem__ as select
def __getitem__(self:DuckDBPyRelation, idxs) -> DuckDBPyRelation:
    return self.select(*idxs) if isinstance(idxs, Union[List, Set, Tuple]) else self.select(idxs)
@patch 
def to_recs(self:DuckDBPyRelation) -> List[Dict[str, Any]]:
    return self.df().to_dict(orient='records')

@patch 
def q(self:DuckDBPyConnection, *args, **kwargs) -> List[Dict[str, Any]]:
    return self.sql(*args, **kwargs).to_recs()

# %% ../nbs/00_core.ipynb 9
@patch # use __getitem__ as select
def __getitem__(self:DuckDBPyRelation, idxs):
    return self.select(*idxs) if isinstance(idxs, Union[List, Set, Tuple]) else self.select(idxs)

# %% ../nbs/00_core.ipynb 13
@patch
def datamodel(self: DuckDBPyConnection, table_name:str) ->List[Dict]:
    info =  self.sql(f"PRAGMA table_info='{table_name}'").fetchall()
    return [{'name': r[1], 'type': r[2], 'nullable': not r[3], 'default': r[4], 'pk': r[5]} for r in info]

# %% ../nbs/00_core.ipynb 14
from dataclasses import field, make_dataclass
def convertTypes(s:str)->type:
    d = {
        # Built-in types
        'BOOLEAN': bool,
        'BLOB': bytearray,  # For bytes, bytearray can be used in Python
        'DOUBLE': float,
        'BIGINT': int,
        'VARCHAR': str,
    
        # NumPy DTypes
        'FLOAT': np.float32,
        'DOUBLE': np.float64,
        'SMALLINT': np.int16,
        'INTEGER': np.int32,
        'BIGINT': np.int64,
        'TINYINT': np.int8,
        'USMALLINT': np.uint16,
        'UINTEGER': np.uint32,
        'UBIGINT': np.uint64,
        'UTINYINT': np.uint8
    }
    if s in d: return d[s]
    if s[:7]=='DECIMAL': return float
    return None


# %% ../nbs/00_core.ipynb 15
@patch
def _metadata(self: DuckDBPyConnection,name:str, type:str='table') -> Dict:
    table = (self.table(name) if type == 'table' else self.view(name))
    query = f"select comment from duckdb_{type}s() "
    where = f"where {type}_name = '{name}' and "
    where +=f"schema_name = current_schema() and internal = False"
    meta = self.sql(query+where).to_recs()[0]
    meta['row_count'] = table.shape[0]
    meta['col_count'] = table.shape[1]  
    return meta
@patch
def metadata(self: DuckDBPyConnection, name:str) -> Dict:
    if name in self.table_names: return self._metadata(name, 'table')
    else: return self._metadata(name, 'view')

# %% ../nbs/00_core.ipynb 18
@patch
def dataclass(self: DuckDBPyConnection, table_name:str, pref='', suf='') -> type:
   fields = self.datamodel(table_name)
   fields = [(pref+f['name']+suf, convertTypes(f['type']) if not f['nullable'] else convertTypes(f['type'])|None , field(default=f['default'])) for f in fields]
   return make_dataclass(table_name, fields)

# %% ../nbs/00_core.ipynb 25
def noop(*args, **kwargs): return None
def identity(x): return x

# %% ../nbs/00_core.ipynb 26
class _Getter: 
    """ A Getter utility check https://github.com/AnswerDotAI/fastlite """
    def __init__(self, name:str='', type:str='', dir:List=[], get=noop): store_attr()    
    def __dir__(self): return self.dir
    def __str__(self): return ", ".join(dir(self))
    def __repr__(self): return f"{self.type}::{self.name}: {str(self)}"
    def __contains__(self, s:str): return s in dir(self)
    def __getitem__(self, k): return self.get(k)
    def __getattr__(self, k):
        if k[0]!='_': return self.get(k)
        else: raise AttributeError 

# %% ../nbs/00_core.ipynb 27
class Table:
    def __init__(self, rel:duckdb.DuckDBPyRelation, db:Database, name:str):
        store_attr()
        self.type='Table'
        self.cls = db.dataclass(name)
        self.meta = db.metadata(name)
        self.rel = self.rel.set_alias(name)    
        self.c = _Getter('Columns', 'Column', rel.columns, rel.select)
    def __dir__(self): return custom_dir(self, [s for s in dir(self.rel) if s[0]!= '_'])
    def __getattr__(self, k): 
        if k[0]=='_': raise AttributeError
        return getattr(self.rel, k)
    def __getitem__(self, idx): return self.rel[idx]
    def __str__(self): return f'"{self.db.schema}"."{self.name}"'
    def __repr__(self): return f'<{self.__class__.__name__}  {self.name} {dir(self.c)}>'
    def _repr_markdown_(self):
        markdown = f"**{self.__class__.__name__}: {self.name}** ({self.meta['row_count']} rows, {self.meta['col_count']} cols)\n"
        if self.meta['comment']: markdown += f"> {self.meta['comment']}"
        markdown = (self.rel.df()).head(10).to_markdown(index=False)
        return markdown
        
class View(Table):
    def __init__(self, rel:duckdb.DuckDBPyRelation, db:Database, name:str):
        super().__init__(rel, db, name) 
        self.type = 'View'
    def __getattr__(self, k): # must be overriden otherwise doesn't work
        if k[0]=='_': raise AttributeError
        return getattr(self.rel, k)

# %% ../nbs/00_core.ipynb 28
def custom_dir(c, add): return dir(type(c)) + list(c.__dict__.keys()) + add

class Database:
    def _current(self: DuckDBPyConnection): return self.sql('select current_catalog, current_schema').fetchone()

    def __init__(self, *args, **kwargs):
        self.conn = duckdb.connect(*args, **kwargs) # original connection object is often called
        self.catalog, self.schema = self.conn.sql('select current_catalog, current_schema').fetchone()
        self.tables =  {}
        self.views = {}
        self.xtra = ['query', 'cursor', 'execute', 'fetchone', 'fetchall', 'sql', 'close', 'table_names', 'view_names', 'dataclass', 'metadata']

    def __dir__(self:Database): return custom_dir(self, self.xtra)  
    def __repr__(self): return f'{self.__class__.__name__} ({self.catalog}::{self.schema})'

    def __getattr__(self:Database, k):
        if k in self.xtra: return getattr(self.conn, k)
        if not isinstance(k, str) and k[0]=='_': raise AttributeError
        return self.table(k, include_views=True)        
          
    def __getitem__(self, k): return self.table(k)
    
    
    def table(self, k):
        if isinstance(k, Union[List, Set, Tuple]): return [self.table(ki) for ki in k]
        if not isinstance(k,str): raise AttributeError
        if self.conn.table(k): 
            tbl = Table(self.conn.table(k), self, k)
            self.tables= {**self.tables, **{k: tbl}}
            return tbl
    
    def view(self, k):
        if isinstance(k, Union[List, Set, Tuple]): return [self.view(ki) for ki in k]
        if not isinstance(k,str): raise AttributeError
        if self.conn.view(k): 
            vw = View(rel=self.conn.view(k), db=self, name=k)
            self.views= {**self.views, **{k: vw}}
            return vw
    
        
    @property # tables
    def t(self:Database): return _Getter('Tables', 'Table', self.conn.table_names, self.table)
    @property # views
    def v(self:Database): return _Getter('Views', 'View', self.conn.view_names, self.view)
    @property # functions
    def fns(self:Database): raise NotImplementedError
    # def fns(self:Database): return _Getter(self, f"SELECT function_name FROM duckdb_functions() WHERE schema_name = '{self.schema}' and internal = False")
    @property # secrets
    def shh(self:Database): raise NotImplementedError
    # def shh(self:Database): return _Getter(self, f"SELECT name FROM duckdb_secrets()")

    def q(self:Database, query:str): return self.conn.sql(query).to_recs()
    
