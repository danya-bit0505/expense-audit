import csv,sys,math,urllib.request
from collections import defaultdict
D=['date','дата'];C=['category','cat','категория'];A=['amount','sum','сумма'];X=['description','desc','описание']
_g=lambda h,a:next((c for c in h if c.strip().lower() in a),None)

def main():
 if len(sys.argv)<2:print('Usage: python audit.py FILE');sys.exit(1)
 src=sys.argv[1];f=src
 if src.startswith('http'):urllib.request.urlretrieve(src,'_t.csv');f='_t.csv'
 rows=load(f);rpt=build_report(src,rows);print(rpt)
 open('report.txt','w',encoding='utf-8').write(rpt);print('Saved: report.txt')

def total_sum(R):return round(sum(r['a']for r in R),2)

def by_cat(R):
 t=defaultdict(float)
 for r in R:t[r['c']]+=r['a']
 return sorted(t.items(),key=lambda x:-x[1])

def top5(R):return sorted(R,key=lambda r:-r['a'])[:5]

def find_dups(R):
 s=defaultdict(list)
 for r in R:s[(r['d'],r['x'],r['a'])].append(r)
 return{k:v for k,v in s.items()if len(v)>1}

def find_anom(R):
 b=defaultdict(list)
 for r in R:b[r['c']].append(r)
 res=[]
 for it in b.values():
  a=[r['a']for r in it]
  if len(a)<2:continue
  m=sum(a)/len(a);s=math.sqrt(sum((x-m)**2 for x in a)/len(a))
  if s:res+=[(r,m+3*s)for r in it if r['a']>m+3*s]
 return sorted(res,key=lambda x:-x[0]['a'])

def find_neg(R):return[r for r in R if r['a']<0]

def summarize(R,dup,an,ng):
 t=total_sum(R);top=by_cat(R)[0]if R else('?',0)
 s=[f'Total expenses: {t}',f'Top category: {top[0]} ({round(top[1]/t*100,1)if t else 0}%)']
 s+=[f'ALERT: {len(dup)} duplicate group(s) - check before paying'if dup else'No duplicates found']
 s+=[f'ALERT: {len(an)} anomaly(s) above 3-sigma threshold'if an else'No anomalies detected']
 s+=[f'NOTE: {len(ng)} negative amount(s) - possible refunds/errors'if ng else'No negative amounts']
 return s

def build_report(src,R):
 dup=find_dups(R);an=find_anom(R);ng=find_neg(R)
 L=['AUDIT REPORT','File:'+src,'Rows:'+str(len(R)),'','=== SUMMARY ===']+summarize(R,dup,an,ng)
 L+=['','TOTAL: '+str(total_sum(R)),'','BY CATEGORY:']+[f' {c}: {round(s,2)}'for c,s in by_cat(R)]
 L+=['','TOP 5:']+[f" {r['d']} {r['c']} {r['x']} {r['a']}"for r in top5(R)]
 L+=['','DUPLICATES:']+([f' {len(v)}x {dt}|{dx}|{a}'for(dt,dx,a),v in dup.items()]or[' none'])
 L+=['','ANOMALIES:']+([f" {r['d']} {r['c']} {round(r['a'],2)} lim={round(l,2)}"for r,l in an]or[' none'])
 L+=['','NEGATIVES:']+([f" {r['d']} {r['c']} {r['a']}"for r in ng]or[' none'])
 return'\n'.join(L)

def load(path):
 with open(path,newline='',encoding='utf-8-sig')as f:
  r=csv.DictReader(f);h=r.fieldnames;dc,cc,ac,xc=_g(h,D),_g(h,C),_g(h,A),_g(h,X)
  if not(dc and cc and ac):sys.exit('missing cols')
  rows=[]
  for row in r:
   try:rows.append({'d':row[dc].strip(),'c':row[cc].strip(),'x':(row[xc]if xc else'').strip(),'a':float(row[ac].replace(',','.').replace(' ',''))})
   except:pass
 return rows

if __name__=='__main__':main()
