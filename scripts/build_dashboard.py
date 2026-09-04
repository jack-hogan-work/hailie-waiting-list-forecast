#!/usr/bin/env python3
"""Build the standalone, self-contained public HAILIE forecast dashboard."""

from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
FINAL = ROOT / "outputs" / "final"
HISTORY = ROOT / "data" / "processed" / "regional_waiting_lists_long.csv"
OUTPUT = ROOT / "outputs" / "HAILIE_dashboard.html"
ENGLAND = "E92000001"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def number(value: str | float) -> float:
    return float(value)


def main() -> None:
    history: dict[str, dict] = {}
    for row in read_csv(HISTORY):
        if not row["households_on_register"]:
            continue
        code = row["Area code"]
        history.setdefault(code, {"name": row["Region"], "history": []})
        history[code]["history"].append({"year": int(row["year"]), "value": int(row["households_on_register"])})

    selections = {row["area_code"]: row for row in read_csv(FINAL / "regional_model_selection.csv")}
    national_selections = read_csv(FINAL / "national_model_selection.csv")
    history_sensitivity = read_csv(FINAL / "national_history_sensitivity.csv")
    selections[ENGLAND] = {
        "primary_model_label": next(row["selected_model_label"] for row in national_selections if row["forecast_role"] == "primary_2026_2028"),
        "extension_model_label": next(row["selected_model_label"] for row in national_selections if row["forecast_role"] == "extension_2026_2030"),
    }

    model_order = ["naive", "drift", "linear_trend", "ses", "holt", "damped_trend", "arima"]
    national_sensitivity = []
    for start_year in ["1998", "2005"]:
        records = [row for row in history_sensitivity if row["history_start_year"] == start_year]
        scores = {
            model: sum(
                float(row["mae_households"])
                for row in records
                if row["model"] == model and row["horizon_years"] in {"1", "2", "3"}
            )
            / 3
            for model in model_order
        }
        ranking = sorted(model_order, key=lambda model: (scores[model], model_order.index(model)))
        labels = {row["model"]: row["model_label"] for row in records}
        national_sensitivity.append({
            "window": f"{start_year}–2025",
            "dampedMae": scores["damped_trend"],
            "dampedRank": ranking.index("damped_trend") + 1,
            "naiveMae": scores["naive"],
            "winner": labels[ranking[0]],
        })

    geographies = {code: value for code, value in history.items() if code == ENGLAND or code.startswith("E12")}
    for value in geographies.values():
        value["primary"] = []
        value["extension"] = []

    for row in read_csv(FINAL / "national_forecast_2026_2028.csv") + read_csv(FINAL / "regional_forecast_2026_2028.csv"):
        geographies[row["area_code"]]["primary"].append({
            "year": int(row["forecast_year"]), "point": number(row["point_forecast"]),
            "lower80": number(row["lower_80"]), "upper80": number(row["upper_80"]),
        })
    for row in read_csv(FINAL / "national_extension_2026_2030.csv") + read_csv(FINAL / "regional_extension_2026_2030.csv"):
        geographies[row["area_code"]]["extension"].append({
            "year": int(row["forecast_year"]), "point": number(row["point_forecast"]),
            "lower80": number(row["lower_80"]) if row.get("lower_80") else None,
            "upper80": number(row["upper_80"]) if row.get("upper_80") else None,
        })
    for code, value in geographies.items():
        value["history"].sort(key=lambda item: item["year"])
        value["primary"].sort(key=lambda item: item["year"])
        value["extension"].sort(key=lambda item: item["year"])
        value["models"] = selections[code]

    ordered = {ENGLAND: geographies.pop(ENGLAND)}
    ordered[ENGLAND]["sensitivity"] = national_sensitivity
    ordered.update(dict(sorted(geographies.items(), key=lambda item: item[1]["name"])))
    page = TEMPLATE.replace("__DATA__", json.dumps(ordered, separators=(",", ":")))
    page = page.replace("__DATE__", date.today().strftime("%-d %B %Y"))
    OUTPUT.write_text(page, encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)} ({len(page):,} bytes)")


TEMPLATE = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="Interactive HAILIE dashboard showing England and regional social housing waiting-list forecasts to 2030.">
<title>HAILIE social housing waiting-list forecast dashboard</title>
<style>
:root{--navy:#102f46;--blue:#176d8d;--teal:#0d6f68;--cyan:#dff5f2;--ink:#14242f;--muted:#526675;--line:#d4dee3;--paper:#fff;--wash:#f1f6f7;--amber:#b56a00}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--wash);color:var(--ink);font:16px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
a{color:#075f82;text-underline-offset:.18em}.skip{position:absolute;left:-9999px}.skip:focus{left:1rem;top:1rem;background:#fff;padding:.7rem;z-index:20}
header{background:var(--navy);color:#fff;padding:1.1rem clamp(1.2rem,5vw,4rem)}.brand{max-width:1240px;margin:auto;display:flex;justify-content:space-between;align-items:center;gap:1rem}.brand strong{font-size:1.25rem;letter-spacing:.08em}.brand span{opacity:.82;font-size:.9rem}
main{max-width:1240px;margin:auto;padding:2.4rem clamp(1rem,4vw,2.7rem) 4rem}.intro{display:grid;grid-template-columns:1.35fr .65fr;gap:2rem;align-items:end}.eyebrow{text-transform:uppercase;letter-spacing:.1em;font-weight:750;color:var(--teal);font-size:.8rem}.intro h1{font-size:clamp(2.15rem,5vw,4.4rem);line-height:1.02;letter-spacing:-.035em;margin:.45rem 0 1rem;max-width:15ch}.intro p{max-width:64ch;font-size:1.08rem;color:var(--muted)}
.controls{background:#fff;border:1px solid var(--line);border-radius:14px;padding:1rem;box-shadow:0 12px 35px #17364a12}.controls label{display:block;font-weight:700;margin-bottom:.4rem}.controls select,.controls button{font:inherit}.controls select{width:100%;min-height:48px;border:2px solid var(--blue);border-radius:8px;padding:.55rem;background:#fff;color:var(--ink)}.toggle{display:grid;grid-template-columns:1fr 1fr;gap:.45rem;margin-top:.8rem}.toggle button{border:1px solid var(--line);background:#fff;border-radius:7px;padding:.65rem;cursor:pointer}.toggle button.active{background:var(--navy);color:#fff;border-color:var(--navy)}button:focus-visible,select:focus-visible,a:focus-visible{outline:3px solid #9a6a00;outline-offset:3px}
.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;margin:2rem 0}.card{background:#fff;border:1px solid var(--line);border-radius:12px;padding:1.15rem;min-height:120px}.card .label{display:block;color:var(--muted);font-size:.86rem}.card .value{display:block;color:var(--navy);font-size:clamp(1.35rem,3vw,2rem);font-weight:760;margin:.25rem 0}.card .note{font-size:.82rem;color:var(--muted)}
.panel{background:#fff;border:1px solid var(--line);border-radius:14px;padding:clamp(1rem,3vw,1.7rem);margin:1.2rem 0}.panel h2{color:var(--navy);font-size:1.4rem;margin:.1rem 0 .35rem}.panel-intro{color:var(--muted);margin-top:0}.chart-wrap{position:relative;width:100%;height:430px;margin-top:1rem}canvas{width:100%;height:100%;display:block}.legend{display:flex;gap:1rem;flex-wrap:wrap;font-size:.85rem;color:var(--muted);margin-top:.8rem}.key{display:inline-flex;align-items:center;gap:.35rem}.swatch{width:22px;height:4px;background:var(--blue)}.swatch.forecast{background:var(--teal)}.swatch.band{height:12px;background:#bfe5e1;border:1px solid #85c7c1}
.answer{font-size:1.08rem;border-left:5px solid var(--teal);padding:.8rem 1rem;background:var(--cyan);margin:1.2rem 0}.grid{display:grid;grid-template-columns:1fr 1fr;gap:1.2rem}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse;font-size:.92rem}caption{text-align:left;font-weight:750;color:var(--navy);margin-bottom:.6rem}th,td{padding:.7rem;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}th:first-child,td:first-child{text-align:left}thead th{background:var(--navy);color:#fff}.rank{font-weight:750;color:var(--navy)}
.method{display:grid;grid-template-columns:repeat(3,1fr);gap:1rem}.method div{border-top:3px solid var(--teal);padding-top:.7rem}.method strong{display:block;color:var(--navy)}.source{font-size:.88rem;color:var(--muted)}footer{background:var(--navy);color:#fff;padding:1.5rem clamp(1.2rem,5vw,4rem)}footer div{max-width:1240px;margin:auto;display:flex;justify-content:space-between;gap:1rem;flex-wrap:wrap}
@media(max-width:850px){.intro,.grid{grid-template-columns:1fr}.cards{grid-template-columns:1fr 1fr}.method{grid-template-columns:1fr}.chart-wrap{height:350px}}@media(max-width:520px){.cards{grid-template-columns:1fr}.toggle{grid-template-columns:1fr}.chart-wrap{height:300px}.brand span{display:none}}
@media print{body{background:#fff}header{background:#fff;color:#000;border-bottom:3px solid var(--navy)}.controls,.toggle{display:none}.panel,.card{break-inside:avoid;box-shadow:none}.chart-wrap{height:330px}footer{background:#fff;color:#000;border-top:1px solid var(--line)}}
</style>
</head>
<body>
<a class="skip" href="#dashboard">Skip to dashboard</a>
<header><div class="brand"><strong>HAILIE</strong><span>Social housing waiting-list outlook · England</span></div></header>
<main id="dashboard">
<section class="intro"><div><div class="eyebrow">Interactive forecast dashboard</div><h1>Where could waiting lists be heading?</h1><p>Explore published local-authority register counts and evidence-led forecasts for England and its nine regions. Use the controls to compare the core three-year outlook with the five-year planning view.</p></div><div class="controls"><label for="geography">Choose an area</label><select id="geography"></select><div class="toggle" role="group" aria-label="Forecast horizon"><button id="core" class="active" aria-pressed="true" type="button">2026–2028 core</button><button id="planning" aria-pressed="false" type="button">2026–2030 planning</button></div></div></section>
<section class="cards" aria-label="Headline figures" aria-live="polite"><div class="card"><span class="label">Latest published count</span><span class="value" id="latest"></span><span class="note">Households · 2025</span></div><div class="card"><span class="label" id="forecast-label">Forecast for 2028</span><span class="value" id="forecast"></span><span class="note" id="forecast-note">Central estimate</span></div><div class="card"><span class="label">Change from 2025</span><span class="value" id="change"></span><span class="note" id="direction"></span></div><div class="card"><span class="label">Selected model</span><span class="value" id="model" style="font-size:1.35rem"></span><span class="note">Chosen by rolling-origin MAE</span></div></section>
<p class="answer" id="answer" aria-live="polite"></p>
<section class="panel" id="national-sensitivity" hidden><h2>National history-window sensitivity</h2><p class="panel-intro">Naive has lower mean Y1–Y3 MAE than damped Holt in both later-history windows. This weakens the directional conclusion without changing the full-history central estimate.</p><div class="table-wrap"><table><caption>Damped-Holt performance when validation starts later; MAE in households</caption><thead><tr><th>History window</th><th>Damped-Holt mean MAE</th><th>Rank</th><th>Naive mean MAE</th><th>Window winner</th></tr></thead><tbody id="sensitivity-body"></tbody></table></div></section>
<section class="panel"><h2 id="chart-title">Observed and forecast households</h2><p class="panel-intro">Historical counts are shown from 2010. Shading shows the empirical 80% range where available. Wider 95% diagnostic ranges are retained only in the technical report because their tails depend on very few extreme observations.</p><div class="chart-wrap"><canvas id="chart" role="img" aria-describedby="chart-key"></canvas></div><div class="legend" id="chart-key"><span class="key"><span class="swatch"></span>Observed</span><span class="key"><span class="swatch forecast"></span>Forecast</span><span class="key"><span class="swatch band"></span>80% range</span></div></section>
<section class="grid"><div class="panel"><h2>Forecast detail</h2><div class="table-wrap"><table><caption id="detail-caption"></caption><thead><tr><th scope="col">Year</th><th scope="col">Central estimate</th><th scope="col">80% range</th></tr></thead><tbody id="detail-body"></tbody></table></div></div><div class="panel"><h2>Regional picture (alphabetical)</h2><p class="panel-intro">Six of nine regions use a naive model that carries 2025 forward. These repeated central estimates are model properties, not evidence of stability. Each estimate is paired with its 80% range. Source-noted breaks include Telford &amp; Wrekin leaving the register series from 31 March 2021 and Epping Forest changing transfer-applicant treatment from 2022–23.</p><div class="table-wrap"><table><caption>Regional models and 2028 social housing waiting-list outlook, shown alphabetically</caption><thead><tr><th scope="col">Region</th><th scope="col">Model</th><th scope="col">2025</th><th scope="col">2028 central</th><th scope="col">2028 80% range</th></tr></thead><tbody id="ranking"></tbody></table></div></div></section>
<section class="panel"><h2>How to read this forecast</h2><div class="method"><div><strong>Published evidence</strong>MHCLG Live Table 600, covering households on local-authority housing registers from 1987 to 2025. The reference date is 1 April up to 2018 and 31 March from 2019 onward.</div><div><strong>Tested models</strong>Seven transparent approaches compared through expanding-window rolling-origin backtesting. ARIMA and SES often collapse to the naive carry-forward on this series, so the seven labels are not seven wholly distinct forecasts.</div><div><strong>Uncertainty shown</strong>Public 80% ranges are based on errors observed when forecasting unseen historical years. Regional five-year planning points have no calculated uncertainty and should not be used as standalone planning forecasts.</div></div><p class="source"><strong>Important:</strong> register counts are an administrative measure of social housing waiting-list demand, not a complete measure of housing need. Separate housing-association waiting lists are not included; applicants can appear on more than one authority register, and the publisher says the total is likely to overstate households still requiring social housing at any one time. The central forecast is not a target or guarantee. Data retrieved 7 August 2026. <a href="HAILIE_final_report.html">Read the full report and methodology, including diagnostic 95% ranges</a>.</p></section>
</main>
<footer><div><span>HAILIE social housing waiting-list forecast</span><span>Build generated __DATE__ · Source: MHCLG Live Table 600</span></div></footer>
<script>
const DATA=__DATA__;const select=document.getElementById('geography');const nf=new Intl.NumberFormat('en-GB',{maximumFractionDigits:0});let horizon='primary';
Object.entries(DATA).forEach(([code,item])=>{const o=document.createElement('option');o.value=code;o.textContent=item.name;select.appendChild(o)});
function pct(v){return `${v>=0?'+':''}${v.toFixed(1)}%`}function range(row,key){return row[key]==null?'—':`${nf.format(row[key])}–${nf.format(row[key.replace('lower','upper')])}`}
function update(){const code=select.value||Object.keys(DATA)[0],item=DATA[code],rows=item[horizon],last=item.history[item.history.length-1],end=rows[rows.length-1],delta=(end.point-last.value)/last.value*100,model=horizon==='primary'?item.models.primary_model_label:item.models.extension_model_label,nationalCore=code==='E92000001'&&horizon==='primary',regionalCore=code!=='E92000001'&&horizon==='primary',naiveCarry=regionalCore&&item.models.primary_model==='naive';
document.getElementById('latest').textContent=nf.format(last.value);document.getElementById('forecast').textContent=nf.format(end.point);document.getElementById('forecast-label').textContent=`Forecast for ${end.year}`;document.getElementById('forecast-note').textContent=nationalCore?'Full-history central estimate':regionalCore?'Selected-model central estimate':'Planning point estimate';document.getElementById('change').textContent=pct(delta);document.getElementById('direction').textContent=nationalCore?'Full-history estimate':naiveCarry?'Naive carry-forward':regionalCore?'Modelled difference':'No directional call';document.getElementById('model').textContent=model;
const sensitivityPanel=document.getElementById('national-sensitivity');if(nationalCore){const later=item.sensitivity[item.sensitivity.length-1];document.getElementById('answer').innerHTML=`<strong>England:</strong> the evidence does not identify a robust national increase or decrease over the next three years. The full-history damped-Holt central estimate is <strong>${nf.format(end.point)} in ${end.year} (${pct(delta)})</strong>, but naive performs better in both later-history sensitivity windows, especially ${later.window}.`;document.getElementById('sensitivity-body').innerHTML=item.sensitivity.map(r=>`<tr><th scope="row">${r.window}</th><td>${nf.format(r.dampedMae)}</td><td>${r.dampedRank} of 7</td><td>${nf.format(r.naiveMae)}</td><td>${r.winner}</td></tr>`).join('');sensitivityPanel.hidden=false}else if(regionalCore){const modelContext=naiveCarry?`The central estimate repeats the 2025 observation because backtesting selected the naive carry-forward model. This is a property of the model, not evidence that the register count will remain unchanged.`:`The selected ${model} model gives a central change of ${pct(delta)} from 2025.`;document.getElementById('answer').innerHTML=`<strong>${item.name}:</strong> ${modelContext} The ${end.year} central estimate is <strong>${nf.format(end.point)}</strong>, with an 80% range of <strong>${range(end,'lower80')}</strong>. Regional backtests do not support a strong directional call.`;sensitivityPanel.hidden=true}else if(code!=='E92000001'&&horizon==='extension'){document.getElementById('answer').innerHTML=`<strong>${item.name}:</strong> this five-year regional extension is a point-only planning scenario using the selected ${model} model. No uncertainty was computed for these regional extension points, so they should not be used as standalone planning forecasts.`;sensitivityPanel.hidden=true}else{document.getElementById('answer').innerHTML=`<strong>${item.name}:</strong> this five-year extension is a point-only planning scenario. The central estimate is <strong>${nf.format(end.point)}</strong>; uncertainty widens with the forecast horizon and no directional call is made.`;sensitivityPanel.hidden=true}
document.getElementById('detail-caption').textContent=`${item.name} ${rows[0].year}–${end.year} forecast`;document.getElementById('detail-body').innerHTML=rows.map(r=>`<tr><th scope="row">${r.year}</th><td>${nf.format(r.point)}</td><td>${range(r,'lower80')}</td></tr>`).join('');if(horizon==='extension'&&code!=='E92000001')document.getElementById('detail-caption').textContent+=` — no uncertainty computed for this regional five-year extension`;draw(item,rows)}
function ranking(){const regions=Object.entries(DATA).filter(([c])=>c!=='E92000001').map(([c,i])=>{const y=i.primary.find(r=>r.year===2028),latest=i.history[i.history.length-1].value;return{name:i.name,model:i.models.primary_model_label,latest,point:y.point,lower:y.lower80,upper:y.upper80}}).sort((a,b)=>a.name.localeCompare(b.name));document.getElementById('ranking').innerHTML=regions.map(r=>`<tr><th scope="row">${r.name}</th><td>${r.model}</td><td>${nf.format(r.latest)}</td><td>${nf.format(r.point)}</td><td>${nf.format(r.lower)}–${nf.format(r.upper)}</td></tr>`).join('')}
function draw(item,forecast){const canvas=document.getElementById('chart'),box=canvas.parentElement.getBoundingClientRect(),dpr=window.devicePixelRatio||1;canvas.width=box.width*dpr;canvas.height=box.height*dpr;const c=canvas.getContext('2d');c.scale(dpr,dpr);const W=box.width,H=box.height,p={l:68,r:22,t:25,b:48},hist=item.history.filter(x=>x.year>=2010),points=hist.concat(forecast.map(x=>({year:x.year,value:x.point}))),vals=points.map(x=>x.value);forecast.forEach(x=>['lower80','upper80'].forEach(k=>{if(x[k]!=null)vals.push(x[k])}));let min=Math.min(...vals),max=Math.max(...vals),pad=(max-min)*.1||1;min=Math.max(0,min-pad);max+=pad;const x=y=>p.l+(y-2010)/(forecast[forecast.length-1].year-2010)*(W-p.l-p.r),yy=v=>p.t+(max-v)/(max-min)*(H-p.t-p.b);
function band(lo,hi,color){if(forecast.some(r=>r[lo]==null))return;c.beginPath();forecast.forEach((r,i)=>{const X=x(r.year),Y=yy(r[hi]);i?c.lineTo(X,Y):c.moveTo(X,Y)});[...forecast].reverse().forEach(r=>c.lineTo(x(r.year),yy(r[lo])));c.closePath();c.fillStyle=color;c.fill()}band('lower80','upper80','#bee4df');
function line(rows,color,width,dash=[]){c.beginPath();rows.forEach((r,i)=>{const X=x(r.year),Y=yy(r.value??r.point);i?c.lineTo(X,Y):c.moveTo(X,Y)});c.strokeStyle=color;c.lineWidth=width;c.setLineDash(dash);c.stroke();c.setLineDash([])}line(hist,'#176d8d',3);line([{year:2025,point:lastValue(item)},...forecast],'#16877e',3,[7,5]);c.beginPath();c.arc(x(2025),yy(lastValue(item)),4,0,Math.PI*2);c.fillStyle='#176d8d';c.fill();canvas.setAttribute('aria-label',`${item.name} chart showing observed register counts from 2010 to 2025 and forecasts to ${forecast[forecast.length-1].year}; solid line is observed, dashed line is forecast, shaded area is the empirical 80% range`)}
function lastValue(item){return item.history[item.history.length-1].value}select.addEventListener('change',update);document.getElementById('core').onclick=()=>{horizon='primary';document.getElementById('core').classList.add('active');document.getElementById('core').setAttribute('aria-pressed','true');document.getElementById('planning').classList.remove('active');document.getElementById('planning').setAttribute('aria-pressed','false');update()};document.getElementById('planning').onclick=()=>{horizon='extension';document.getElementById('planning').classList.add('active');document.getElementById('planning').setAttribute('aria-pressed','true');document.getElementById('core').classList.remove('active');document.getElementById('core').setAttribute('aria-pressed','false');update()};window.addEventListener('resize',update);ranking();update();
</script>
</body></html>'''


if __name__ == "__main__":
    main()
