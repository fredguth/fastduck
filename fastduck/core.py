# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/00_core.ipynb.

# %% ../nbs/00_core.ipynb 1
from __future__ import annotations
import duckdb
from duckdb import DuckDBPyConnection, DuckDBPyRelation
from typing import List, Dict, Optional, Union, Any, Tuple, Set, Literal
from fastcore.all import store_attr, patch, L
import numpy as np
import pandas as pd
from dataclasses import field, make_dataclass
from fastcore.xtras import hl_md, dataclass_src
from functools import wraps, partial
from pathlib import Path


# %% auto 0
__all__ = ['props', 'database', 'convertTypes', 'clean', 'custom_dir', 'create_patch_property', 'create_prop', 'noop', 'identity',
           'RemoteSqliteError', 'InvalidPathError', 'find_matches']

# %% ../nbs/00_core.ipynb 13
@wraps(duckdb.connect)
def database(*args, **kwargs):
    db = duckdb.connect(*args, **kwargs)
    return db

# %% ../nbs/00_core.ipynb 16
def _current(self: DuckDBPyConnection): return self.sql('select current_catalog, current_schema').fetchone()
@patch(as_prop=True)
def catalog(self: DuckDBPyConnection): return _current(self)[0]

@patch(as_prop=True)
def schema(self: DuckDBPyConnection): return _current(self)[1]

@patch(as_prop=True) # just the name part in the alias
def name(self:DuckDBPyRelation): return self.alias.split('.')[-1]

@patch
def __getitem__(self:DuckDBPyRelation, idxs) -> DuckDBPyRelation: # selecting by passing a list of column names
    return self.select(*idxs) if isinstance(idxs, Union[List, Set, Tuple]) else self.select(idxs)
@patch 
def to_recs(self:DuckDBPyRelation) -> List[Dict[str, Any]]:
    '''The relation as a list of records'''
    return self.df().to_dict(orient='records')
@patch 
def to_list(self:DuckDBPyRelation) -> List[List]:
    '''The relation as a list'''
    return [list(r.values()) if len(r.values())>1 else list(r.values())[0] for r in self.to_recs() ]
@patch 
def q(self:DuckDBPyConnection, *args, **kwargs) -> List[Dict[str, Any]]:
    '''Run a query and return the result as a list of records'''
    return self.sql(*args, **kwargs).to_recs()



# %% ../nbs/00_core.ipynb 20
@patch(as_prop=True)
def tables(self: DuckDBPyConnection) -> DuckDBPyRelation:
    '''Returns the tables in the database'''
    return self.sql(f"""
        select distinct database_name as catalog, schema_name as schema, table_name as name,
        'BASE TABLE' as type, comment from duckdb_tables() union all 
        select distinct database_name as catalog, schema_name as schema, view_name as name, 
        'VIEW' as type, comment from duckdb_views() where internal=False order by catalog, type, name""")
    
@patch(as_prop=True)
def views(self: DuckDBPyConnection) -> DuckDBPyRelation:
    '''Returns the views in current schema'''
    return self.tables.filter(f"type =='VIEW' and catalog='{self.catalog}' and schema = '{self.schema}'")
@patch(as_prop=True)
def base_tables(self: DuckDBPyConnection) -> DuckDBPyRelation:
    '''Returns the base tables in current schema'''
    return self.tables.filter(f"type =='BASE TABLE' and catalog='{self.catalog}' and schema = '{self.schema}'")

@patch(as_prop=True)
def schemas(self: DuckDBPyConnection) -> DuckDBPyRelation:
    '''Returns the schemas in the database'''
    return self.tables.project(f"catalog || '_' || schema as catalog_schema").distinct()


# %% ../nbs/00_core.ipynb 24
@patch
def datamodel(self: DuckDBPyConnection, table_name:str) ->List[Dict]:
    ''' Returns the data model of a table or view. 
    The columns names, types, nullable status, default value and
    primary key status.'''
    
    return [{'name': r[1], 'type': r[2], 'nullable': not r[3], 'default': r[4], 'pk': r[5]} 
            for r in self.sql(f"PRAGMA table_info='{table_name}'").fetchall()]

# %% ../nbs/00_core.ipynb 26
def convertTypes(s:str)->type:
    ''' Convert DuckDB types to Python and Numpy types'''
    d = {
        # Built-in types
        'BOOLEAN': bool,
        'BLOB': bytearray,  # For bytes, bytearray can be used in Python
        'DOUBLE': float,
        'BIGINT': int,
        'VARCHAR': str,
        'VARCHAR[]': str,
    
        # NumPy DTypes
        'FLOAT': np.float32,
        'DOUBLE': float,
        'SMALLINT': np.int16,
        'INTEGER': np.int32,
        'TINYINT': np.int8,
        'USMALLINT': np.uint16,
        'UINTEGER': np.uint32,
        'UBIGINT': np.uint64,
        'UTINYINT': np.uint8,
        'TIMESTAMP': np.timedelta64
    }
    if s in d: return d[s]
    if s[:7]=='DECIMAL': return float
    raise ValueError(f'Unknown type {s}')


import re, keyword
def clean(s):
    s = re.sub(r'\W|^(?=\d)', '_', s)
    return s + '_' if keyword.iskeyword(s) else s

@patch
def dataclass(self: DuckDBPyConnection, 
              table_name:str, # table or view name
              pref='', # prefix to add to the field names
              suf='', # suffix to add to the field names
              cls_name:str = None # defaults to table_name
              ) -> type:
    '''Creates a `dataclass` type from a table or view in the database.'''
    cls_name = cls_name or table_name
    fields = self.datamodel(table_name)
    fields = [(clean(pref+f['name']+suf), convertTypes(f['type']) if not f['nullable'] else convertTypes(f['type'])|None , field(default=f['default'])) for f in fields]
    return make_dataclass(table_name, fields)

# %% ../nbs/00_core.ipynb 32
_saved = {}

def _set_attr(obj, k, v): #hash to avoid collisions
    _saved[str(hash(obj)) + '_' + k] = v

def _get_attr(obj, key):
    k = str(hash(obj)) + '_' + key
    return _saved[k] if k in _saved else None

@patch
def _set(self: DuckDBPyRelation, k, v):
    _set_attr(self, k, v)

@patch
def _get(self: DuckDBPyRelation, key):
    return _get_attr(self, key)

@patch
def _set(self: DuckDBPyConnection, k, v):
    _set_attr(self, k, v)

@patch
def _get(self: DuckDBPyConnection, key):
    return _get_attr(self, key)


def custom_dir(c, add): return sorted(dir(type(c)) + list(c.__dict__.keys()) if hasattr(c, '__dict__') else [] + add)

def create_patch_property(name):
    @patch(as_prop=True)
    def prop(self: DuckDBPyRelation):
        return self._get(name)
    return prop

props = ['cls', 'rel', 'model', 'meta']
for p in props: setattr(DuckDBPyRelation, p, create_patch_property(p))

@patch
def __dir__(self:DuckDBPyRelation) -> List[str]: return custom_dir(DuckDBPyRelation, props)
    
def create_prop(c, name, f): setattr(c, name, property(f))
@patch(as_prop=True)
def cls(self:DuckDBPyRelation): return self._get('cls')

@patch(as_prop=True)
def model(self:DuckDBPyRelation): return self._get('model')

@patch(as_prop=True)
def meta(self:DuckDBPyRelation): return self._get('meta')

@patch(as_prop=True)
def rel(self:DuckDBPyRelation): return self._get('rel')


@patch
def table(self:DuckDBPyConnection, name:str, schema:str= None, catalog:str=None) -> DuckDBPyRelation:
    if isinstance(name, Union[List, Set, Tuple]): return [self.table(n) for n in name]
    if not isinstance(name,str): raise AttributeError
    r = self.tables.filter(f"name == '{name}' and schema == '{schema or self.schema}' and catalog =='{catalog or self.catalog}'")
    catalog, schema, name, type, comment = r.fetchone()
    tbl = self.sql(f"from {catalog}.{schema}.{name}")
    tbl = tbl.set_alias(f"{catalog}.{schema}.{name}")
    tbl._set('cls', self.dataclass(name))
    tbl._set('model', self.datamodel(name))
    meta = {'base': self, 'catalog': catalog, 'schema': schema, 'name': name, 'type': type, 'comment': comment, 'shape': tbl.shape}
    tbl._set('meta', meta)
    tbl._set('rel', tbl)
    return tbl



# %% ../nbs/00_core.ipynb 33
@patch
def _select(self:DuckDBPyRelation, k) -> DuckDBPyRelation:
    return self.select(k) if isinstance(k, str) else self.select(*k)

@patch(as_prop=True)
def c(self:DuckDBPyRelation): 
    '''Column autocomplete'''
    return _Getter(self, 'column', self.columns, self._select)

# %% ../nbs/00_core.ipynb 36
def noop(*args, **kwargs): return None
def identity(x): return x


class _Getter: 
    """ A Getter utility check https://github.com/AnswerDotAI/fastlite """
    def __init__(self, db:DuckDBPyConnection, type:str='', dir:List=[], get=noop): store_attr()    
    def __dir__(self): return self.dir
    def __str__(self): return ", ".join(dir(self))
    def __repr__(self): return f"{str(self.db).split(' ')[-1]} {self.type.title()}s: {str(self)}"
    def __contains__(self, s:str): return s in dir(self)
    def __getitem__(self, k): return self.get(k)
    def __getattr__(self, k):
        if k[0]!='_': return self.get(k)
        else: raise AttributeError 

@patch
def use(self:DuckDBPyConnection, catalog_schema:str=None, catalog:str=None, schema=None) -> None:
    if not catalog_schema and not catalog and not schema: return self
    catalog, schema = catalog_schema.split('_') if catalog_schema else (catalog, schema)
    catalog = catalog or self.catalog
    schema = schema or self.schema
    self.sql(f"use {catalog}.{schema}")

@patch
def get_schema(self: DuckDBPyConnection, catalog_schema: str):
    self.use(catalog_schema)
    self._set(catalog_schema, self)
    return self

@patch(as_prop=True) # tables
def s(self:DuckDBPyConnection): 
    '''Autocomplete functonality for schemas'''
    return _Getter(self, 'schema', self.tables.project(f"catalog || '_' || schema").distinct().to_list(), self.get_schema)
@patch(as_prop=True) # tables
def t(self:DuckDBPyConnection): 
    '''Autocomplete functonality for tables'''
    return _Getter(self,'table', self.base_tables.select('name').to_list(), self.table)
@patch(as_prop=True) # views
def v(self:DuckDBPyConnection): 
    '''Autocomplete functonality for views'''
    return _Getter(self, 'view', self.views.select('name').to_list(), self.table)
@patch(as_prop=True) # functions
def fns(self:DuckDBPyConnection): raise NotImplementedError
# def fns(self:DuckDBPyConnection): return _Getter(self, f"SELECT function_name FROM duckdb_functions() WHERE schema_name = '{self.schema}' and internal = False")

@patch(as_prop=True) # secrets
def shh(self:DuckDBPyConnection): raise NotImplementedError
# def shh(self:DuckDBPyConnection): return _Getter(self, f"SELECT name FROM duckdb_secrets()")

@patch
def __repr__(self:DuckDBPyConnection): return f'{self.__class__.__name__} ({self.catalog}_{self.schema})'


# %% ../nbs/00_core.ipynb 43
@patch
def __str__(self:DuckDBPyRelation): return f'{self.alias}'

@patch
def __repr__(self:DuckDBPyRelation): 
    return f"{self.__class__.__name__} {self.meta['type'] if self.meta else ''} {self.alias if self.alias[:7]!='unnamed' else ''} \n\n"
@patch
def _repr_markdown_(self: DuckDBPyRelation): 
    markdown =  f"#### {self.__repr__()} "
    if self.meta and self.meta['comment']: markdown += f"> {self.meta['comment']}\n\n"
    df = self.df()
    if self.shape[0] > 5: 
        head = df.head(3)
        tail = df.tail(2)
        ellipsis = pd.DataFrame([["..."] * df.shape[1]], columns=df.columns)
        df = pd.concat([head, ellipsis, tail])
    markdown += df.to_markdown(index=False, tablefmt="pipe")
    markdown += f"\n\n {self.shape[0]} rows  x  {self.shape[1]} cols "
    return markdown

@patch
def _repr_html_(self: DuckDBPyRelation):
   
    df = self.df()
    if self.shape[0] > 5: 
        head = df.head(3)
        tail = df.tail(2)
        ellipsis = pd.DataFrame([["..."] * df.shape[1]], columns=df.columns)
        df = pd.concat([head, ellipsis, tail])
    h = df.to_html(index=False)
    h += f"<p>{self.shape[0]} rows x  {self.shape[1]} cols &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{self.__class__.__name__} {self.meta['type'].replace(' ', '_') if self.meta else ''} {self.alias if self.alias[:7]!='unnamed' else ''} </p>"
    h += f"<p><i>{self.meta['comment']}</i></p>\n\n" if self.meta and self.meta['comment'] else ''
    return h




# %% ../nbs/00_core.ipynb 59
class RemoteSqliteError(Exception): pass
class InvalidPathError(Exception): pass

@patch
def attach(self: DuckDBPyConnection, path, read_only:bool = False, type:Literal['duckdb' | 'sqlite']='duckdb', catalog_name:str=None) -> None:
    type = 'sqlite' if Path(path).suffix =='.sqlite' else type
    if path.startswith(('s3://', 'gcp://', 'https://')):
        self.install_extension('httpfs')
        self.load_extension('httpfs')
        read_only = True
        if type =='sqlite': raise RemoteSqliteError('Cannot attach to a remote sqlite database.')
    elif not Path(path).exists(): raise InvalidPathError(f"Couldn't find {path}")
    self.install_extension('sqlite')
    self.load_extension('sqlite')
    o = "(TYPE sqlite, " if type=='sqlite' else "("
    o += f"READ_ONLY  {read_only})"
    q = f"'{path}' {'AS ' + catalog_name if catalog_name else ''} {o}"
    self.sql(f"ATTACH {q}")

# %% ../nbs/00_core.ipynb 65
def find_matches(pattern: str, items: List[str]) -> List[str]:
    regex_pattern = re.compile(pattern)
    return [item for item in items if regex_pattern.match(item)]
    
@patch
def __contains__(self:DuckDBPyConnection, name:str):
    schm, _, tbl = name.rpartition('.')
    return tbl in self.tables.filter(f"schema = '{schm or self.schema}'").select('name').to_list()

@patch
def drop(self: DuckDBPyConnection, pattern: str):
    '''Drop a table or view'''
    schm, _, tbl = pattern.rpartition('.')
    schm = schm or self.schema
    dropping = find_matches('.'.join([schm, tbl]), [rec['schema']+'.'+rec['name'] for rec in self.tables.filter(f"catalog = '{self.catalog}'").to_recs()])
    for tbl in dropping: self.sql(f"DROP TABLE {tbl}")

# %% ../nbs/00_core.ipynb 69
@patch
def _create(self: DuckDBPyConnection, type: str, fileglob: str, table_name: Optional[str] = None, 
            filetype: Optional[Literal['csv', 'xlsx', 'json', 'parquet', 'sqlite']] = None, 
            replace: bool = False, as_name: Optional[str] = None, *args, **kwargs):
    filepath, name = Path(fileglob), as_name or table_name or Path(fileglob).stem
    if name in self and not replace: raise ValueError(f"Table {name} already exists")
    self.drop(name)
    filetype = filetype or filepath.suffix[1:]
    options = ', '.join(f"{k}={repr(v)}" for k, v in kwargs.items())
    
    if filetype == 'sqlite':
        self.install_extension('sqlite'), self.load_extension('sqlite')
        self.sql(f"CREATE {type} {name} AS SELECT * FROM sqlite_scan('{filepath}', {table_name} {options})")
    elif filetype == 'xlsx':
        self.install_extension('spatial'), self.load_extension('spatial')
        self.sql(f"CREATE {type} {name} AS SELECT * FROM st_read('{filepath}' {options})")
    else:
        getattr(self, f'read_{filetype}')(fileglob, *args, **kwargs).to_table(name)

@patch
def create_table(self: DuckDBPyConnection, 
                 fileglob: str, # file path or glob
                 table_name: Optional[str] = None, # table name
                 filetype: Optional[Literal['csv', 'xlsx', 'json', 'parquet', 'sqlite']] = None, # file type
                 as_name:Optional[str]=None ,
                 replace: bool = False, # replace existing table
                 *args, **kwargs 
                 ):
    '''Create a table from a file'''
    return self._create('TABLE', fileglob, table_name, filetype, replace, as_name, *args, **kwargs)

@patch
def create_view(self: DuckDBPyConnection, 
                 fileglob: str, # file path or glob
                 view_name: Optional[str] = None, # view name
                 filetype: Optional[Literal['csv', 'xlsx', 'json', 'parquet', 'sqlite']] = None, # file type
                 replace: bool = False,  # replace existing view
                 as_name:Optional[str]=None ,
                 *args, **kwargs
                 ):
    '''Create a view from a file'''
    return self._create('VIEW', fileglob, view_name, filetype, replace, as_name, *args, **kwargs)
    

# %% ../nbs/00_core.ipynb 86
@patch
def import_from(self:DuckDBPyConnection, filepath=None, pre='', suf='', schema=None, replace=None):
    self.attach(filepath, catalog_name='import')
    list =  self.tables.filter("catalog = 'import' and type='BASE TABLE'").select('name').to_list()
    self.sql('detach import')
    schema = schema or self.schema
    db.sql(f"CREATE SCHEMA IF NOT EXISTS {schema}")
    for tbl in list: db.create_table(fileglob=filepath, filetype='sqlite', table_name=tbl, as_name=schema+'.'+pre+tbl+suf, replace=replace)
