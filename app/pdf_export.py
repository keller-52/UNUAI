"""Local PDF export through installed Chrome/Edge, with explicit render acknowledgement."""
import os,shutil,subprocess,tempfile,secrets,threading
from pathlib import Path
from urllib.parse import urlencode
from core import require,ValidationError
JOBS={}
GUARD=threading.BoundedSemaphore(2)

def browser_path():
 candidates=[os.environ.get('PAPER_AI_BROWSER','')]
 for name in ('google-chrome','google-chrome-stable','chromium','chromium-browser','msedge'):candidates.append(shutil.which(name) or '')
 for root in (os.environ.get('PROGRAMFILES',''),os.environ.get('PROGRAMFILES(X86)',''),os.environ.get('LOCALAPPDATA','')):
  if root:
   candidates.extend(str(Path(root)/x) for x in ('Google/Chrome/Application/chrome.exe','Microsoft/Edge/Application/msedge.exe'))
 candidates.extend(['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome','/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge'])
 return next((x for x in candidates if x and Path(x).is_file()),None)

def acknowledge(job_id,success,error=''):
 if job_id in JOBS:JOBS[job_id]={'ready':success,'error':str(error)[:1000]}

def export_pdf(port,ids,view,token=''):
 browser=browser_path()
 require(browser is not None,'PDF_BROWSER_MISSING')
 require(GUARD.acquire(blocking=False),'PDF_EXPORT_BUSY')
 job=secrets.token_urlsafe(24);JOBS[job]={'ready':False,'error':''}
 try:
  with tempfile.TemporaryDirectory(prefix='paper-pdf-') as folder:
   output=Path(folder)/'paper.pdf'
   params={'ids':','.join(ids),'view':view,'pdf_job':job}
   if token:params['token']=token
   url=f'http://127.0.0.1:{port}/print.html?'+urlencode(params)
   command=[browser,'--headless','--disable-gpu','--no-first-run','--no-default-browser-check',
            '--no-pdf-header-footer','--virtual-time-budget=15000','--timeout=45000',
            '--user-data-dir='+str(Path(folder)/'profile'),'--print-to-pdf='+str(output),url]
   try:result=subprocess.run(command,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=60)
   except (subprocess.TimeoutExpired,OSError):raise ValidationError('PDF_EXPORT_FAILED') from None
   require(JOBS[job]['ready'],JOBS[job]['error'] or 'PDF_RENDER_NOT_READY')
   require(result.returncode==0 and output.is_file(),'PDF_EXPORT_FAILED')
   data=output.read_bytes();require(data.startswith(b'%PDF-') and len(data)>500,'PDF_EXPORT_FAILED')
   return data
 finally:JOBS.pop(job,None);GUARD.release()
