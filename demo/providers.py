"""Provider-specific HTTP contracts; no SDK or credentials bundled."""
import json,re
from urllib.parse import quote,urlsplit
from core import require,ValidationError

PRESETS={
 'deepseek':{'label':'DeepSeek','protocol':'chat','base_url':'https://api.deepseek.com','model':'deepseek-flash'},
 'openai':{'label':'OpenAI','protocol':'responses','base_url':'https://api.openai.com/v1','model':''},
 'anthropic':{'label':'Anthropic / Claude','protocol':'anthropic','base_url':'https://api.anthropic.com/v1','model':''},
 'gemini':{'label':'Google / Gemini','protocol':'gemini','base_url':'https://generativelanguage.googleapis.com/v1beta','model':''},
 'qwen':{'label':'Alibaba / Qwen','protocol':'dashscope','base_url':'https://dashscope.aliyuncs.com/api/v1','model':'qwen-plus'},
 'doubao':{'label':'Volcengine / Doubao','protocol':'chat','base_url':'https://ark.cn-beijing.volces.com/api/v3','model':''},
 'kimi':{'label':'Moonshot / Kimi','protocol':'chat','base_url':'https://api.moonshot.cn/v1','model':''},
 'glm':{'label':'Zhipu / GLM','protocol':'chat','base_url':'https://open.bigmodel.cn/api/paas/v4','model':''},
 'minimax':{'label':'MiniMax','protocol':'anthropic','base_url':'https://api.minimax.io/anthropic/v1','model':''},
 'azure':{'label':'Azure OpenAI','protocol':'azure_responses','base_url':'https://YOUR-RESOURCE.openai.azure.com/openai/v1','model':''},
 'xai':{'label':'xAI / Grok','protocol':'chat','base_url':'https://api.x.ai/v1','model':''},
 'mistral':{'label':'Mistral','protocol':'chat','base_url':'https://api.mistral.ai/v1','model':''},
 'groq':{'label':'Groq','protocol':'chat','base_url':'https://api.groq.com/openai/v1','model':''},
 'baidu':{'label':'Baidu / ERNIE','protocol':'chat','base_url':'https://qianfan.baidubce.com/v2','model':''},
 'hunyuan':{'label':'Tencent / Hunyuan','protocol':'chat','base_url':'https://api.hunyuan.cloud.tencent.com/v1','model':''},
 'custom':{'label':'Custom','protocol':'chat','base_url':'https://api.openai.com/v1','model':''},
}
PROTOCOLS=('chat','responses','azure_responses','anthropic','gemini','dashscope')

def validate_provider(p):
 require(p.get('protocol','chat') in PROTOCOLS,'Unknown API protocol')
 require(p.get('provider','custom') in PRESETS,'Unknown provider preset')
 u=urlsplit(p['base_url'])
 require(u.scheme=='https' and u.hostname and not u.username and not u.password and not u.query and not u.fragment,'Use an HTTPS provider URL without credentials')
 require(p.get('json_mode','auto') in ('auto','on','off'),'Invalid JSON mode')
 return p

def build_request(p,messages,budget):
 validate_provider(p)
 base=p['base_url'].rstrip('/');protocol=p.get('protocol','chat');model=p['model'];key=p['api_key']
 headers={'Content-Type':'application/json','Authorization':'Bearer '+key}
 system='\n'.join(m['content'] for m in messages if m['role']=='system')
 turns=[m for m in messages if m['role']!='system']
 mode=p.get('json_mode','auto');use_json=mode=='on' or mode=='auto' and (protocol in ('responses','azure_responses','gemini') or urlsplit(base).hostname in ('api.deepseek.com','api.openai.com'))
 if protocol in ('responses','azure_responses'):
  url=base+'/responses';payload={'model':model,'instructions':system,'input':turns,'max_output_tokens':budget,'store':False}
  if use_json:payload['text']={'format':{'type':'json_object'}}
  if protocol=='azure_responses':headers={'Content-Type':'application/json','api-key':key}
 elif protocol=='anthropic':
  url=base+'/messages';headers={'Content-Type':'application/json','x-api-key':key,'anthropic-version':'2023-06-01'}
  payload={'model':model,'system':system,'messages':turns,'max_tokens':budget}
 elif protocol=='gemini':
  url=base+'/models/'+quote(model.removeprefix('models/'),safe='')+':generateContent'
  headers={'Content-Type':'application/json','x-goog-api-key':key}
  payload={'systemInstruction':{'parts':[{'text':system}]},'contents':[{'role':'model' if m['role']=='assistant' else 'user','parts':[{'text':m['content']}]} for m in turns],'generationConfig':{'maxOutputTokens':budget}}
  if use_json:payload['generationConfig']['responseMimeType']='application/json'
 elif protocol=='dashscope':
  url=base+'/services/aigc/text-generation/generation'
  payload={'model':model,'input':{'messages':messages},'parameters':{'result_format':'message','max_tokens':budget,'enable_thinking':False}}
  if use_json:payload['parameters']['response_format']={'type':'json_object'}
 else:
  url=base+'/chat/completions';payload={'model':model,'messages':messages,'max_tokens':budget}
  if use_json:payload['response_format']={'type':'json_object'}
  if urlsplit(base).hostname=='api.deepseek.com':payload['thinking']={'type':'disabled'}
 return url,headers,payload

def response_content(body,p):
 protocol=p.get('protocol','chat');finish=None;usage=body.get('usage',body.get('usageMetadata'))
 if protocol in ('responses','azure_responses'):
  content=''.join(c.get('text','') for item in body.get('output',[]) if item.get('type')=='message' for c in item.get('content',[]) if c.get('type')=='output_text')
  finish=body.get('status')
 elif protocol=='anthropic':
  content=''.join(c.get('text','') for c in body['content'] if c.get('type')=='text');finish=body.get('stop_reason')
 elif protocol=='gemini':
  c=body.get('candidates',[]);require(bool(c),'AI returned no candidates; check provider safety response')
  content=''.join(x.get('text','') for x in c[0].get('content',{}).get('parts',[]) if not x.get('thought'));finish=c[0].get('finishReason')
 else:
  output=body.get('output',body) if protocol=='dashscope' else body
  choice=output['choices'][0];content=choice['message']['content'];finish=choice.get('finish_reason')
 require(isinstance(content,str) and len(content)<=180000,'Missing or excessive model content')
 return content,finish,usage

def parse_json_content(content):
 s=content.strip()
 # Harmless wrappers are common even when the underlying object is correct.
 if s.startswith('```'):
  s=re.sub(r'^```(?:json)?\s*','',s,flags=re.I);s=re.sub(r'\s*```$','',s)
 try:return json.loads(s)
 except json.JSONDecodeError:
  start=s.find('{')
  if start>=0:
   obj,end=json.JSONDecoder().raw_decode(s[start:])
   require(not s[start+end:].strip() or not s[start+end:].lstrip().startswith('{'),'Multiple AI JSON objects')
   return obj
  raise
