"""Exact supported config mappings. Unsupported fields never become partial PASS."""
import copy
import math
from jsonschema import Draft202012Validator

def _object(properties):
    return {'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}
TEXT={'type':'string','minLength':1}
CONFIG_SCHEMAS={
    **{kind:_object({'text':TEXT}) for kind in ('text.required_exact','text.forbidden_exact','markdown.required_exact','markdown.forbidden_exact')},
    **{kind:_object({'max_words':{'type':'integer','minimum':0}}) for kind in ('text.word_limit','markdown.word_limit')},
    'json.field_exact':_object({'field':TEXT,'expected':{}}),
    'csv.columns':_object({'columns':{'type':'array','minItems':1,'maxItems':50,'uniqueItems':True,'items':TEXT}}),
    'csv.rows_exact':_object({'source_id':TEXT}),
    'csv.total_cap':_object({'column':TEXT,'max_value':{'type':'number'}}),
}

for kind in ('text.word_limit','markdown.word_limit'):
    CONFIG_SCHEMAS[kind]['description']='Maximum word count only. Minimum word constraints are unsupported; min_words is not accepted.'

def schemas():return copy.deepcopy(CONFIG_SCHEMAS)

def config_problem(kind,config):
    schema=CONFIG_SCHEMAS.get(kind)
    if schema is None:return None  # Unsupported kinds are handled by the existing abstention path.
    errors=list(Draft202012Validator(schema).iter_errors(config))
    if errors:return 'Unsupported or invalid '+kind+' configuration: '+errors[0].message
    if kind=='csv.total_cap' and not math.isfinite(config['max_value']):return 'Unsupported nonfinite numeric cap'
    return None

def requirement_schema():
    """Discriminated configs; unknown kinds are explicitly unresolved rather than guessed."""
    branches=[]
    for kind,config in schemas().items():
        branches.append({'type':'object','additionalProperties':False,'required':['id','kind','description','mode','config'],
            'properties':{'id':TEXT,'kind':{'const':kind},'description':TEXT,'mode':{'enum':['must_change','must_preserve','unknown']},'config':config}})
    branches.append({'type':'object','additionalProperties':False,'required':['id','kind','description','mode','config'],
        'properties':{'id':TEXT,'kind':{'type':'string','not':{'enum':list(CONFIG_SCHEMAS)}},'description':TEXT,'mode':{'enum':['must_change','must_preserve','unknown']},'config':{'type':'object'}},
        'description':'Native XLSX/DOCX retain their existing exact guards. Other unknown kinds remain UNKNOWN; this branch does not establish coverage.'})
    return {'oneOf':branches}
