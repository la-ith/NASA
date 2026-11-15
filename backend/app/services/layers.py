"""Private point-supported map layers. No interpolated field/national raster is invented."""
from math import isfinite
from app.adapters import content_hash

METRICS = {
    'precipitation': ('Season rainfall', 'mm per season', 'historical_analysis'),
    'et0': ('Reference evapotranspiration', 'mm per season', 'historical_analysis'),
    'etc_standard': ('Standard crop demand', 'mm per season', 'conditional_simulation'),
    'rainfed_deficit': ('Rain-fed deficit', 'mm per season', 'conditional_simulation'),
    'irrigated_net_irrigation': ('Net irrigation need', 'mm per season', 'conditional_simulation'),
    'rainfed_stress_days': ('Rain-fed stress days', 'days per season', 'conditional_simulation'),
}


def manifests(analysis):
    items=[]
    for strategy in analysis['strategies']:
        for metric,(title,unit,kind) in METRICS.items():
            data=strategy['result']['summary'][metric]['spread']
            items.append(dict(id=f"{strategy['id']}:{metric}",title=title,quantity=metric,unit=unit,
                strategy_id=strategy['id'],analysis_id=analysis['analysis_id'],result_type=kind,
                status='available' if data else 'unavailable',period=analysis['period'],
                spatial_support='analyzed point; regional climate and soil-map-unit inputs',
                geometry_type='Point',native_resolution=analysis['provenance']['weather']['returned_support'],
                legend=dict(type='continuous',method='numeric values, not agronomic suitability',
                            palette=['#2166ac','#f7f7f7','#b2182b']),
                source_versions=analysis['versions'],
                geojson_url=f"/api/v2/analyses/{analysis['analysis_id']}/layers/{strategy['id']}:{metric}/geojson",
                limitations=['Point result cannot be expanded into a national heatmap.',
                             'Zooming does not increase source resolution.'],
                artifact_id=content_hash([analysis['analysis_id'],strategy['id'],metric,data])))
    return items


def feature(analysis,layer_id,year=None):
    sid,_,metric=layer_id.partition(':')
    if metric not in METRICS:raise KeyError(layer_id)
    strategy=next((s for s in analysis['strategies'] if s['id']==sid),None)
    if strategy is None:raise KeyError(layer_id)
    stats=strategy['result']['summary'][metric]['spread']
    value=None if stats is None else stats['median']
    if year is not None:
        season=next((s for s in strategy['result']['seasons'] if s['year']==year),None)
        value=season.get(metric) if season else None
    point=analysis['location']['public_location']
    return dict(type='Feature',geometry=dict(type='Point',coordinates=[point['lon'],point['lat']]),
        properties=dict(analysis_id=analysis['analysis_id'],strategy_id=sid,quantity=metric,
            value=value if value is None or isfinite(value) else None,unit=METRICS[metric][1],
            result_type=METRICS[metric][2],statistic='season value' if year is not None else 'historical median',
            year=year,status='unavailable' if value is None else 'available',
            location_precision='generalized for display; not the original field geometry',
            spatial_support='point summary, not a continuous surface'))


def compare(analysis,a,b,metric):
    if metric not in METRICS:raise KeyError(metric)
    by_id={s['id']:s for s in analysis['strategies']}
    if a not in by_id or b not in by_id:raise KeyError('strategy')
    def values(s):return {r['year']:r[metric] for r in s['result']['seasons'] if r.get(metric) is not None}
    av,bv=values(by_id[a]),values(by_id[b])
    common=sorted(av.keys()&bv.keys())
    from app.science.statistics import spread
    from dataclasses import asdict
    distribution=spread([av[y]-bv[y] for y in common])
    return dict(quantity=metric,unit=METRICS[metric][1],operation='A minus B, paired by year',
                strategy_a=a,strategy_b=b,paired_years=common,
                distribution=None if distribution is None else asdict(distribution),
                differences=[dict(year=y,value=av[y]-bv[y]) for y in common],
                limitation='Different crop calendars may expose strategies to different days within the same year. '
                           'Difference is conditional simulation, not proven causal impact.')
