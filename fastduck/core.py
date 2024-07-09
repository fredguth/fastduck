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
from IPython.display import Markdown


# %% auto 0
__all__ = ['props', 'database', 'convertTypes', 'clean', 'custom_dir', 'create_patch_property', 'create_prop', 'noop', 'identity']

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
def tables(self: DuckDBPyConnection, catalog:str=None) -> DuckDBPyRelation:
    '''Returns a dictionary of tables in the database'''
    q = f"from {catalog or self.catalog}.information_schema.tables"
    s = f"'{catalog or self.catalog}' as catalog, table_schema as schema, table_name as name, table_type as type, table_comment as comment"
    return self.sql(q).distinct().select(s)

@patch(as_prop=True)
def views(self: DuckDBPyConnection) -> DuckDBPyRelation:
    '''Returns a dictionary of views in the database'''
    return self.tables.filter(f"type =='VIEW' and catalog='{self.catalog}' and schema = '{self.schema}'")
@patch(as_prop=True)
def base_tables(self: DuckDBPyConnection) -> DuckDBPyRelation:
    '''Returns a dictionary of views in the database'''
    return self.tables.filter(f"type =='BASE TABLE' and catalog='{self.catalog}' and schema = '{self.schema}'")

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

@patch
def _set(self:DuckDBPyRelation, k, v):
    global _saved
    # use hash to avoid clashes
    _saved[str(hash(self))+'_'+k] = v

@patch
def _get(self:DuckDBPyRelation, key):
    global _saved
    k = str(hash(self))+'_'+key
    return _saved[k] if k in _saved else None

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



# %% ../nbs/00_core.ipynb 34
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
def use(self:DuckDBPyConnection, catalog_schema:str=None, catalog:str=None, schema=None):
    catalog, schema = catalog_schema.split('_')
    self.sql(f"use {catalog}.{schema}")
    print("Using ", self)
    return self

@patch(as_prop=True) # tables
def s(self:DuckDBPyConnection): 
    '''Autocomplete functonality for schemas'''
    return _Getter(self, 'schema', self.tables.project(f"catalog || '_' || schema").distinct().to_list(), self.use)
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


# %% ../nbs/00_core.ipynb 40
@patch
def __str__(self:DuckDBPyRelation): return f'{self.alias}'

@patch
def __repr__(self:DuckDBPyRelation): 
    return f"<{self.__class__.__name__} {self.meta['type'] if self.meta else ''} **{self.alias}** ({self.shape[0]} rows, {self.shape[1]} cols)>\n\n"
@patch
def _repr_markdown_(self: DuckDBPyRelation): 
    markdown =  f"{self.__repr__()}\n\n"
    if self.meta and self.meta['comment']: markdown += f"> {self.meta['comment']}\n\n"
    df = self.df()
    if self.shape[0] > 5: 
        head = df.head(3)
        tail = df.tail(2)
        ellipsis = pd.DataFrame([["..."] * df.shape[1]], columns=df.columns)
        df = pd.concat([head, ellipsis, tail])
    markdown += df.to_markdown(index=False)
    return markdown


