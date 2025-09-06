# 📊 Analysis Metadata Integration - COMPLETE

## ✅ **Enhancement: Model Usage Transparency**

The JSON output now includes comprehensive analysis metadata showing which models were used and whether LLM or rule-based algorithms were applied for each agent.

---

## 🔧 **Enhanced JSON Response Structure**

### **New Schema Fields**

```json
{
  "issues": [...],
  "meta": [...],
  "extraction_info": {...},
  "analysis_metadata": {
    "analysis_methods": [
      {
        "agent": "PICO-Parser",
        "method": "rule-based|llm-enhanced|hybrid",
        "llm_model": "anthropic/claude-3.5-haiku",
        "llm_provider": "openrouter",
        "fallback_reason": "LLM authentication failed"
      }
    ],
    "llm_available": false,
    "total_llm_calls": 0,
    "total_tokens_used": null,
    "estimated_cost": null
  }
}
```

### **Analysis Method Types**
- **`rule-based`** - Traditional pattern matching and validation rules
- **`llm-enhanced`** - LLM-powered analysis with domain-specific prompts  
- **`hybrid`** - Combination of rule-based + LLM validation (future)

---

## 📋 **Example Response**

### **Current Response (Without API Keys)**
```bash
curl -X POST http://127.0.0.1:8000/review/start -d @manuscript.json
```

**Analysis Metadata:**
```json
{
  "analysis_metadata": {
    "analysis_methods": [
      {
        "agent": "PICO-Parser",
        "method": "rule-based",
        "fallback_reason": "LLM authentication failed"
      },
      {
        "agent": "PRISMA-Checker", 
        "method": "rule-based"
      },
      {
        "agent": "Risk-of-Bias",
        "method": "rule-based", 
        "fallback_reason": "LLM authentication failed"
      },
      {
        "agent": "Meta-Analysis",
        "method": "rule-based"
      }
    ],
    "llm_available": false,
    "total_llm_calls": 0
  }
}
```

### **Future Response (With API Keys)**
**Analysis Metadata:**
```json
{
  "analysis_metadata": {
    "analysis_methods": [
      {
        "agent": "PICO-Parser",
        "method": "llm-enhanced",
        "llm_model": "anthropic/claude-3.5-haiku",
        "llm_provider": "openrouter"
      },
      {
        "agent": "PRISMA-Checker",
        "method": "rule-based"
      },
      {
        "agent": "Risk-of-Bias", 
        "method": "llm-enhanced",
        "llm_model": "anthropic/claude-3.5-sonnet",
        "llm_provider": "openrouter"
      },
      {
        "agent": "Meta-Analysis",
        "method": "rule-based"
      }
    ],
    "llm_available": true,
    "total_llm_calls": 2,
    "total_tokens_used": 1250,
    "estimated_cost": 0.0034
  }
}
```

---

## 🎯 **Method Transparency by Agent**

| Agent | Current Method | With API Keys | Fallback Behavior |
|-------|---------------|---------------|-------------------|
| **PICO-Parser** | `rule-based` | `llm-enhanced` | ✅ Graceful fallback |
| **PRISMA-Checker** | `rule-based` | `rule-based` | ✅ No LLM needed |
| **Risk-of-Bias** | `rule-based` | `llm-enhanced` | ✅ Graceful fallback |  
| **Meta-Analysis** | `rule-based` | `rule-based` | ✅ Statistical methods |

---

## 🔍 **Fallback Reason Tracking**

### **Possible Fallback Reasons:**
- `"LLM authentication failed"` - API key authentication issues
- `"LLM disabled by parameter"` - Explicit `use_llm=false` parameter
- `"LLM agents not available"` - Import/dependency issues
- `"Cost limit exceeded"` - Daily spending limit reached
- `"Model unavailable"` - Specific model not accessible

---

## 🚀 **Client Usage Examples**

### **JavaScript/TypeScript Client**
```typescript
interface AnalysisMetadata {
  analysis_methods: AnalysisMethod[]
  llm_available: boolean
  total_llm_calls: number
  total_tokens_used?: number
  estimated_cost?: number
}

interface AnalysisMethod {
  agent: string
  method: 'rule-based' | 'llm-enhanced' | 'hybrid'
  llm_model?: string
  llm_provider?: string
  fallback_reason?: string
}

// Usage
const response = await fetch('/review/start', {
  method: 'POST',
  body: JSON.stringify(manuscript)
})
const result = await response.json()

// Check analysis methods
result.analysis_metadata?.analysis_methods.forEach(method => {
  console.log(`${method.agent}: ${method.method}`)
  if (method.llm_model) {
    console.log(`  Using ${method.llm_provider}/${method.llm_model}`)
  }
  if (method.fallback_reason) {
    console.log(`  Fallback: ${method.fallback_reason}`)
  }
})
```

### **Python Client**
```python
import requests

response = requests.post('/review/start', json=manuscript_data)
result = response.json()

# Check analysis quality
metadata = result.get('analysis_metadata', {})
print(f"LLM Available: {metadata.get('llm_available', False)}")
print(f"LLM Calls Made: {metadata.get('total_llm_calls', 0)}")

# Show method breakdown
for method in metadata.get('analysis_methods', []):
    status = method['method']
    agent = method['agent']
    
    if method.get('llm_model'):
        print(f"{agent}: {status} using {method['llm_provider']}/{method['llm_model']}")
    else:
        print(f"{agent}: {status}")
        if method.get('fallback_reason'):
            print(f"  Reason: {method['fallback_reason']}")
```

---

## ⚡ **Performance & Cost Tracking**

### **Future Enhancements Ready**
- **Token Usage Tracking**: Actual tokens consumed per request
- **Cost Estimation**: Real-time cost calculation based on model pricing
- **Performance Metrics**: Analysis time per agent
- **Quality Scores**: LLM vs rule-based accuracy comparison

### **Cost Management Integration**
```json
{
  "analysis_metadata": {
    "total_tokens_used": 1250,
    "estimated_cost": 0.0034,
    "cost_breakdown": {
      "PICO-Parser": { "tokens": 800, "cost": 0.0008 },
      "Risk-of-Bias": { "tokens": 450, "cost": 0.0026 }
    },
    "daily_usage": {
      "total_cost": 2.34,
      "limit": 10.00,
      "remaining": 7.66
    }
  }
}
```

---

## ✅ **Integration Status**

**✅ COMPLETE**: Analysis metadata fully integrated across all endpoints
- `/review/start` - JSON manuscript analysis with metadata
- `/review/upload` - DOCX upload analysis with metadata  
- `/review/enhanced` - Explicit LLM control with metadata

**🎯 Benefits**:
- **Full Transparency** - Clients know exactly which methods were used
- **Quality Assurance** - Track when LLM enhancement is active vs fallback
- **Cost Management** - Monitor usage and spending in production
- **Debugging** - Clear fallback reasons for troubleshooting
- **Analytics** - Usage patterns and method effectiveness tracking

**🚀 Ready for Production**: Complete method transparency and tracking system implemented!

---

*Generated: $(date)*
*Systematic Review Auditor - Enhanced Platform with Metadata Tracking*