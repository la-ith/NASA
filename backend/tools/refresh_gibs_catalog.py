"""Refresh the allowlisted NASA WMTS contracts; retain exact date gaps, legends and source hash."""
import asyncio
import datetime
import hashlib
import json
import sys
from pathlib import Path
import xml.etree.ElementTree as ET
import httpx

ROOT=Path(__file__).resolve().parents[2]
URL='https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/1.0.0/WMTSCapabilities.xml'
IDS={'IMERG_Precipitation_Rate':('imerg_rain_rate','mm/hr','Daily precipitation-rate imagery, not accumulated seasonal rainfall'),
     'SMAP_L4_Analyzed_Surface_Soil_Moisture':('smap_surface','m3/m3','12:00 UTC model-assimilated surface moisture, 0–5 cm'),
     'SMAP_L4_Analyzed_Root_Zone_Soil_Moisture':('smap_root_zone','m3/m3','12:00 UTC model-assimilated root-zone moisture, 0–100 cm')}


def extract(raw):
    ns={'w':'http://www.opengis.net/wmts/1.0','o':'http://www.opengis.net/ows/1.1'}
    href='{http://www.w3.org/1999/xlink}href'
    layers=[]
    for x in ET.fromstring(raw).findall('.//w:Layer',ns):
        ident=x.findtext('o:Identifier',namespaces=ns)
        if ident not in IDS:continue
        alias,unit,meaning=IDS[ident]
        layers.append(dict(id=alias,provider='NASA GIBS',source_layer=ident,title=x.findtext('o:Title',namespaces=ns),
            unit=unit,meaning=meaning,intervals=[v.text for v in x.findall('w:Dimension/w:Value',ns)],
            default_date=x.findtext('w:Dimension/w:Default',namespaces=ns),matrix_set='GoogleMapsCompatible_Level6',
            maxzoom=6,tile_size=256,tile_template=next(v.attrib['template'] for v in x.findall('w:ResourceURL',ns)
                if '{Time}' in v.attrib.get('template','') and v.attrib.get('resourceType')=='tile'),
            legend_url=x.find('w:Style/w:LegendURL',ns).attrib[href],
            colormap_url=next(m.attrib[href] for m in x.findall('o:Metadata',ns) if 'v1.3/' in m.attrib.get(href,'')),
            quantitative_pixel_query=False,scope='US50 display mask; source valid pixels vary by date and product'))
    if len(layers)!=3:raise ValueError('NASA capabilities lack an expected allowlisted layer')
    return dict(capabilities_url=URL,retrieved_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                capabilities_sha256=hashlib.sha256(raw).hexdigest(),layers=layers)


async def main():
    if len(sys.argv)>1:raw=Path(sys.argv[1]).read_bytes()
    else:
        async with httpx.AsyncClient(timeout=40) as c:
            r=await c.get(URL);r.raise_for_status();raw=r.content
    (ROOT/'data/catalogs/nasa_gibs_layers.json').write_text(json.dumps(extract(raw),indent=2),encoding='utf-8')


if __name__=='__main__':asyncio.run(main())
