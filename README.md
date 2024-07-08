# fastduck


<!-- WARNING: THIS FILE WAS AUTOGENERATED! DO NOT EDIT! -->

`fastduck` provides some development experience improvements for the
standard `duckdb` python API.

## Install

``` sh
pip install fastduck
```

## How to use

~~import fastduck as fuck~~

``` python
from fastduck import database
```

``` python
db = database('../data/chinook.duckdb')
db
```

    DuckDBPyConnection (chinook_main)

``` python
dt = db.t
dt
```

    (chinook_main) Tables: Album, Artist, Customer, Employee, Genre, Invoice, InvoiceLine, MediaType, Playlist, PlaylistTrack, Track, fd_Customer, todos, tst

You can use this to grab a single table…

``` python
artist = dt.Artist
artist
```

\<DuckDBPyRelation BASE TABLE **chinook.main.Artist** (275 rows, 2
cols)\>

| ArtistId | Name                  |
|:---------|:----------------------|
| 1        | AC/DC                 |
| 2        | Accept                |
| 3        | Aerosmith             |
| …        | …                     |
| 274      | Nash Ensemble         |
| 275      | Philip Glass Ensemble |

``` python
customer = dt['Customer']
customer
```

\<DuckDBPyRelation BASE TABLE **chinook.main.Customer** (59 rows, 13
cols)\>

| CustomerId | FirstName | LastName   | Company                                          | Address                         | City                | State | Country | PostalCode | Phone              | Fax                | Email                    | SupportRepId |
|:-----------|:----------|:-----------|:-------------------------------------------------|:--------------------------------|:--------------------|:------|:--------|:-----------|:-------------------|:-------------------|:-------------------------|:-------------|
| 1          | Luís      | Gonçalves  | Embraer - Empresa Brasileira de Aeronáutica S.A. | Av. Brigadeiro Faria Lima, 2170 | São José dos Campos | SP    | Brazil  | 12227-000  | +55 (12) 3923-5555 | +55 (12) 3923-5566 | luisg@embraer.com.br     | 3            |
| 2          | Leonie    | Köhler     |                                                  | Theodor-Heuss-Straße 34         | Stuttgart           |       | Germany | 70174      | +49 0711 2842222   |                    | leonekohler@surfeu.de    | 5            |
| 3          | François  | Tremblay   |                                                  | 1498 rue Bélanger               | Montréal            | QC    | Canada  | H2G 1A7    | +1 (514) 721-4711  |                    | ftremblay@gmail.com      | 3            |
| …          | …         | …          | …                                                | …                               | …                   | …     | …       | …          | …                  | …                  | …                        | …            |
| 58         | Manoj     | Pareek     |                                                  | 12,Community Centre             | Delhi               |       | India   | 110017     | +91 0124 39883988  |                    | manoj.pareek@rediff.com  | 3            |
| 59         | Puja      | Srivastava |                                                  | 3,Raj Bhavan Road               | Bangalore           |       | India   | 560001     | +91 080 22289999   |                    | puja_srivastava@yahoo.in | 3            |

… or multiple tables at once:

``` python
dt['Artist', 'Album', 'Genre']
```

    [<DuckDBPyRelation BASE TABLE **chinook.main.Artist** (275 rows, 2 cols)>
     ,
     <DuckDBPyRelation BASE TABLE **chinook.main.Album** (347 rows, 3 cols)>
     ,
     <DuckDBPyRelation BASE TABLE **chinook.main.Genre** (25 rows, 2 cols)>
     ]

It also provides auto-complete in Jupyter, IPython and nearly any other
interactive Python environment:

<img src="images/autocomplete.png" width="400"
alt="Autocomplete in Jupyter" />

You can check if a table is in the database already:

``` python
'Artist' in dt
```

    True

Column work in a similar way to tables, using the `c` property:

``` python
ac = artist.c
ac, artist.columns
```

    (chinook.main.Artist Columns: ArtistId, Name, ['ArtistId', 'Name'])

Auto-complete works for columns too:

<img src="images/columns_complete.png" width="300"
alt="Columns autocomplete in Jupyter" />

The tables and views of a database got some interesting new attributes….

``` python
artist.meta
```

    {'base': DuckDBPyConnection (chinook_main),
     'catalog': 'chinook',
     'schema': 'main',
     'name': 'Artist',
     'type': 'BASE TABLE',
     'comment': None,
     'shape': (275, 2)}

``` python
artist.model
```

    [{'name': 'ArtistId',
      'type': 'INTEGER',
      'nullable': False,
      'default': None,
      'pk': True},
     {'name': 'Name',
      'type': 'VARCHAR',
      'nullable': True,
      'default': None,
      'pk': False}]

``` python
artist.cls, type(artist.cls)
```

    (fastduck.core.Artist, type)

`duckdb` replacement scans keep working and are wonderful for usage in
SQL statements:

``` python
db.sql("select * from artist where artist.Name like 'AC/%'")
```

\<DuckDBPyRelation **unnamed_relation_88ad0e8a5a0890ad** (1 rows, 2
cols)\>

| ArtistId | Name  |
|---------:|:------|
|        1 | AC/DC |

You can view the results of a query as records

``` python
db.sql("select * from artist where artist.Name like 'AC/%'").to_recs()
```

    [{'ArtistId': 1, 'Name': 'AC/DC'}]

or as a list of lists

``` python
db.sql("select * from artist where artist.Name like 'AC/%'").to_list()
```

    [[1, 'AC/DC']]

And you there is also an alias for `sql` with `to_recs` simply called
`q`

``` python
db.q("select * from artist where artist.Name like 'AC/%'")
```

    [{'ArtistId': 1, 'Name': 'AC/DC'}]

#### Dataclass support

As we briefly saw, a `dataclass` type with the names, types and defaults
of the table is added to the Relation:

``` python
abm = db.t.Album
art = db.t.Artist
acca_sql = f"""
select abm.* 
from abm join art using (ArtistID)
where art.Name like 'AC/%'
"""
acca_dacca = db.q(acca_sql)
acca_dacca
```

    [{'AlbumId': 1,
      'Title': 'For Those About To Rock We Salute You',
      'ArtistId': 1},
     {'AlbumId': 4, 'Title': 'Let There Be Rock', 'ArtistId': 1}]

``` python
let_b_rock_obj = abm.cls(**acca_dacca[-1])
let_b_rock_obj
```

    Album(AlbumId=4, Title='Let There Be Rock', ArtistId=1)

You can get the definition of the dataclass using fastcore’s
`dataclass_src` – everything is treated as nullable, in order to handle
auto-generated database values:

``` python
from fastcore.xtras import hl_md, dataclass_src

src = dataclass_src(db.t.Album.cls)
hl_md(src, 'python')
```

``` python
@dataclass
class Album:
    AlbumId: int32 = None
    Title: str = None
    ArtistId: int32 = None
```
