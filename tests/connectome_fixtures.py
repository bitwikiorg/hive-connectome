from __future__ import annotations

import json
import zipfile

import pyarrow as pa
import pyarrow.feather as feather
from pathlib import Path
from xml.sax.saxutils import escape


def _cell(ref: str, value):
    if isinstance(value, (int, float)):
        return f'<c r="{ref}"><v>{value}</v></c>'
    return f'<c r="{ref}" t="inlineStr"><is><t>{escape(str(value))}</t></is></c>'


def _sheet(rows: list[list[tuple[str, object]]]) -> str:
    body=[]
    for index,cells in enumerate(rows, start=1):
        body.append(f'<row r="{index}">'+''.join(_cell(ref,val) for ref,val in cells)+"</row>")
    return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +         '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>' + ''.join(body) + '</sheetData></worksheet>'


def write_cook_fixture(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    chemical = _sheet([
        [], [],
        [('D3','ALML'),('E3','AVM'),('F3','ASHL')],
        [('C4','ALML'),('D4',0),('E4',4),('F4',2)],
        [('C5','AVM'),('D5',1),('E5',0),('F5',3)],
        [('C6','ASHL'),('D6',2),('E6',1),('F6',0)],
    ])
    gap = _sheet([
        [], [],
        [('D3','ALML'),('E3','AVM'),('F3','ASHL')],
        [('C4','ALML'),('D4',0),('E4',1),('F4',0)],
        [('C5','AVM'),('D5',1),('E5',0),('F5',1)],
        [('C6','ASHL'),('D6',0),('E6',1),('F6',0)],
    ])
    workbook='''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>
<sheet name="hermaphrodite chemical" sheetId="1" r:id="rId1"/>
<sheet name="hermaphrodite gap jn symmetric" sheetId="2" r:id="rId2"/>
</sheets></workbook>'''
    rels='''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>
</Relationships>'''
    with zipfile.ZipFile(path,'w') as zf:
        zf.writestr('xl/workbook.xml',workbook)
        zf.writestr('xl/_rels/workbook.xml.rels',rels)
        zf.writestr('xl/worksheets/sheet1.xml',chemical)
        zf.writestr('xl/worksheets/sheet2.xml',gap)


def write_malecns_fixture(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data={
        'schemaVersion':1,
        'source':'test MaleCNS fixture',
        'neurons':[
            {'id':'1','type':'sens','role':'sensory','annotations':{'superclass':'sensory_neuron'}},
            {'id':'2','type':'asc','role':'ascending','annotations':{'superclass':'ascending_neuron'}},
            {'id':'3','type':'int','role':'other','annotations':{}},
            {'id':'4','type':'motor','role':'motor','annotations':{}},
        ],
        'edges':[[0,2,900],[1,2,700],[2,3,1200],[3,2,-300]],
    }
    path.write_text(json.dumps(data),encoding='utf-8')


def install_runtime_fixtures(data_dir: Path) -> None:
    write_cook_fixture(data_dir/'connectomes'/'worm-cook-2020'/'cook_2020_adjacency.xlsx')
    write_malecns_fixture(data_dir/'connectomes'/'fly-malecns-locomotor'/'locomotor_circuit.json')


def write_malecns_full_fixture(data_dir: Path) -> Path:
    root=data_dir/'connectomes'/'fly-malecns-v1'
    root.mkdir(parents=True,exist_ok=True)
    annotations=pa.table({
        'bodyId':pa.array([10,20,30,40,50],type=pa.int64()),
        'superclass':['sensory_neuron','interneuron','descending_neuron','ascending_neuron','glia'],
        'status':['Traced','Traced','Traced','Traced','Glia'],
    })
    neurotransmitters=pa.table({
        'body':pa.array([10,20,30,40,50],type=pa.int64()),
        'consensus_nt':['acetylcholine','gaba','acetylcholine','glutamate','acetylcholine'],
    })
    edges=pa.table({
        'body_pre':pa.array([10,20,30,40,50],type=pa.int64()),
        'body_post':pa.array([20,30,40,10,10],type=pa.int64()),
        'weight':pa.array([5,7,3,11,100],type=pa.int64()),
    })
    feather.write_feather(annotations,root/'annotations.feather')
    feather.write_feather(neurotransmitters,root/'neurotransmitters.feather')
    feather.write_feather(edges,root/'edges.feather')
    return root
