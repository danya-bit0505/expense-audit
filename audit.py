import csv,sys,math,os,urllib.request
from collections import defaultdict
DATE=['date','data','datum','дата']
CAT=['category','cat','тип','категория']
AMT=['amount','sum','total','сумма']
DESC=['description','desc','описание']
def _c(h,a):return next((x for x in h if x.strip().lower() in a),None)

def main():
 if len(sys.argv)<2:print('Usage: python audit.py FILE');sys.exit(1)
 src=sys.argv[1];rows=load(get_file(src));rpt=build_report(src,rows);print(rpt)
 p=os.path.join(os.path.dirname(os.path.abspath(__file__)),'report.txt')
 open(p,'w',encoding='utf-8').write(rpt);print('Saved:'+p)

def summarize(rows,d,an,ng):
 t=total_sum(rows);top=by_category(rows)[0]if rows else('?',0)
 pct=round(top[1]/t*100,1)if t else 0
 s=[f'Total expenses: {t}',f'Largest category: {top[0]} ({pct}% of total)']
 s.append(f'ALERT: {len(d)} duplicate group(s) - verify before paying'if d else'No duplicates found')
 s.append(f'ALERT: {len(an)} anomaly(s) above 3-sigma threshold'if an else'No anomalies detected')
 s.append(f'NOTE: {len(ng)} negative amount(s) - possible refunds/errors'if ng else'No negative amounts')
 return s

def find_anomalies(rows):
 b=defaultdict(list)
 for r in rows:b[r['cat']].append(r)
 res=[]
 for it in b.values():
  a=[r['amt']for r in it]
  if len(a)<2:continue
  m=sum(a)/len(a);s=math.sqrt(sum((x-m)**2 for x in a)/len(a))
  if s:res+=[(r,m+3*s)for r in it if r['amt']>m+3*s]
 return sorted(res,key=lambda x:-x[0]['amt'])

def find_duplicates(rows):
 s=defaultdict(list)
 for r in rows:s[(r['date'],r['desc'],r['amt'])].append(r)
 return{k:v for k,v in s.items()if len(v)>1}

def find_negatives(rows):return[r for r in rows if r['amt']<0]

def build_report(src,rows):
 d=find_duplicates(rows);an=find_anomalies(rows);ng=find_negatives(rows)
 L=['EXPENSE AUDIT REPORT','File:'+src,'Rows:'+str(len(rows)),
    '','=== SUMMARY ===']
 L+=summarize(rows,d,an,ng)
 L+=['','1. TOTAL: '+str(total_sum(rows)),
     '','2. BY CATEGORY:']+[f'  {c}: {round(s,2)}'for c,s in by_category(rows)]
 L+=['','3. TOP 5:']+[f"  {r['date']} {r['cat']} {r['desc']} {r['amt']}"for r in top5(rows)]
 L+=['','4. DUPLICATES:']+([f'  {len(g)}x {dt}|{de}|{a}'for(dt,de,a),g in d.items()]or['  none'])
 L+=['','5. ANOMALIES:']+([f"  {r['date']} {r['cat']} {round(r['amt'],2)} lim={round(l,2)}"for r,l in an]or['  none'])
 L+=['','6. NEGATIVES:']+([f"  {r['date']} {r['cat']} {r['amt']}"for r in ng]or['  none'])
 return'\n'.join(L)

def get_file(s):
 if s.startswith('http'):urllib.request.urlretrieve(s,'_tmp.csv');return'_tmp.csv'
 return s

def load(path):
 with open(path,newline='',encoding='utf-8-sig')as f:
  r=csv.DictReader(f);h=r.fieldnames;d,c,a,x=_c(h,DATE),_c(h,CAT),_c(h,AMT),_c(h,DESC)
  if not(d and c and a):sys.exit('missing cols')
  rows=[]
  for row in r:
   try:rows.append({'date':row[d].strip(),'cat':row[c].strip(),
    'desc':(row[x]if x else'').strip(),'amt':float(row[a].replace(',','.').replace(' ',''))})
   except:pass
 return rows

def total_sum(rows):return round(sum(r['amt']for r in rows),2)

def by_category(rows):
 t=defaultdict(float)
 for r in rows:t[r['cat']]+=r['amt']
 return sorted(t.items(),key=lambda x:-x[1])

def top5(rows):return sorted(rows,key=lambda r:-r['amt'])[:5]

if __name__=='__main__':main()
