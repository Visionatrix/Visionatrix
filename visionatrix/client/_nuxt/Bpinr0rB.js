import{_ as F,a as A}from"./Dy5WZDO9.js";import{f as I,u as C,q as P,s as L,v as N,g as $,x as k,n as B,y as q,h as y,w as i,p as E,o as c,a,b as l,j as o,c as M,d as u,i as v,k as j,l as H}from"./BiplqXYw.js";import{_ as T,a as D}from"./CR-CQ5rX.js";import{_ as R,a as K}from"./CZa9KWOn.js";const W={class:"flex flex-col md:flex-row"},J={class:"px-5 pb-5 md:w-4/5"},Q={key:0,class:"admin-settings mb-3"},X={class:"flex items-center"},Y={class:"flex items-center"},Z={class:"flex items-center"},ee={key:1,class:"upload-flow mb-5 py-4 rounded-md"},te={class:"flex items-center space-x-3"},le={class:"user-settings mb-3"},de=I({__name:"index",setup(oe){C({title:"Settings - Visionatrix",meta:[{name:"description",content:"Settings - Visionatrix"}]});const V=[{label:"Settings",icon:"i-heroicons-cog-6-tooth-20-solid",to:"/settings"},{label:"Workers information",icon:"i-heroicons-chart-bar-16-solid",to:"/settings/workers"}],_=P(),t=L(),p=N();function h(){console.debug("Saving settings",t.settingsMap),Promise.all(Object.keys(t.settingsMap).map(n=>t.settingsMap[n].admin&&_.isAdmin?t.saveGlobalSetting(t.settingsMap[n].key,t.settingsMap[n].value,t.settingsMap[n].sensitive):t.saveUserSetting(t.settingsMap[n].key,t.settingsMap[n].value))).then(()=>{p.add({title:"Settings saved",description:"Settings saved successfully"})}).catch(n=>{p.add({title:"Error saving setting",description:n.message})})}const m=$(),x=k(null),w=k(!1);function U(){const n=x.value.$refs.input.files[0]||null;if(!n){p.add({title:"No file selected",description:"Please select a file to upload"});return}w.value=!0,m.uploadFlow(n).then(e=>{if(console.debug("uploadFlow",e),e&&"detail"in e&&(e==null?void 0:e.detail)!==""){p.add({title:"Error uploading flow",description:e.detail});return}else p.add({title:"Flow uploaded",description:"Flow uploaded successfully"});x.value.$refs.input.value=""}).catch(e=>{console.debug("uploadFlow error",e),p.add({title:"Error uploading flow",description:e.message})}).finally(()=>{w.value=!1})}return B(()=>m.outputMaxSize,()=>{m.saveUserOptions()}),q(()=>{t.loadAllSettings()}),(n,e)=>{const S=F,z=j,r=T,d=R,g=A,b=K,f=H,O=D,G=E;return c(),y(G,{class:"lg:h-dvh"},{default:i(()=>[a("div",W,[l(S,{links:V,class:"md:w-1/5"}),a("div",J,[o(_).isAdmin?(c(),M("div",Q,[e[16]||(e[16]=a("h3",{class:"mb-3 text-xl font-bold"},"Admin preferences (global settings)",-1)),a("div",X,[l(z,{name:"i-heroicons-question-mark-circle",class:"mr-2 text-amber-400"}),e[13]||(e[13]=a("p",{class:"text-amber-400"},[a("span",null,"Access tokens are required for "),a("a",{class:"hover:underline underline-offset-4",href:"https://visionatrix.github.io/VixFlowsDocs/GatedModels.html",target:"_blank"},"gated models"),u(". ")],-1))]),l(d,{size:"md",class:"py-3",label:"Huggingface Auth token",description:"Bearer authentication token from your Huggingface account to allow downloading gated models with limited access."},{default:i(()=>[l(r,{modelValue:o(t).settingsMap.huggingface_auth_token.value,"onUpdate:modelValue":e[0]||(e[0]=s=>o(t).settingsMap.huggingface_auth_token.value=s),placeholder:"Huggingface Auth token",class:"w-full",type:"password",icon:"i-heroicons-shield-check",size:"md",autocomplete:"off"},null,8,["modelValue"])]),_:1}),l(g,{class:"mt-3",label:"Gemini"}),e[17]||(e[17]=a("p",{class:"text-slate text-sm text-orange-300 dark:text-orange-100 text-center"},"Can be used by flows and as a translation provider",-1)),l(d,{size:"md",class:"py-3",label:"Google API key"},{description:i(()=>e[14]||(e[14]=[u(" Global Google API key, required for Flows, e.g. where ComfyUI-Gemini Node is used. Instruction how to obtain key "),a("a",{class:"hover:underline font-bold",href:"https://ai.google.dev/gemini-api/docs/api-key"},"here",-1),u(". ")])),default:i(()=>[l(r,{modelValue:o(t).settingsMap.google_api_key.value,"onUpdate:modelValue":e[1]||(e[1]=s=>o(t).settingsMap.google_api_key.value=s),placeholder:"Google API key",class:"w-full",type:"password",icon:"i-heroicons-shield-check",size:"md",autocomplete:"off"},null,8,["modelValue"])]),_:1}),l(d,{size:"md",class:"py-3",label:"Gemini model",description:"Override Gemini model to use."},{default:i(()=>[a("div",Y,[l(b,{modelValue:o(t).settingsMap.gemini_model.value,"onUpdate:modelValue":e[2]||(e[2]=s=>o(t).settingsMap.gemini_model.value=s),color:"white",variant:"outline",placeholder:"Select Gemini model",options:o(t).settingsMap.gemini_model.options},null,8,["modelValue","options"]),o(t).settingsMap.gemini_model.value?(c(),y(f,{key:0,icon:"i-heroicons-x-mark",variant:"outline",color:"white",class:"ml-2",onClick:e[3]||(e[3]=()=>o(t).settingsMap.gemini_model.value="")})):v("",!0)])]),_:1}),l(d,{size:"md",class:"py-3",label:"Proxy (for Google)"},{description:i(()=>e[15]||(e[15]=[u(" Proxy to access Gemini configuration "),a("a",{class:"hover:underline font-bold",href:"https://visionatrix.github.io/VixFlowsDocs/AdminManual/Installation/proxy_gemini/"},"string",-1),u(". ")])),default:i(()=>[l(r,{modelValue:o(t).settingsMap.google_proxy.value,"onUpdate:modelValue":e[4]||(e[4]=s=>o(t).settingsMap.google_proxy.value=s),placeholder:"Proxy",class:"w-full",type:"text",size:"md",autocomplete:"off"},null,8,["modelValue"])]),_:1}),l(g,{class:"mt-3",label:"Ollama"}),e[18]||(e[18]=a("p",{class:"text-slate text-sm text-orange-300 dark:text-orange-100 text-center"},"Can be used by flows and as a translation provider",-1)),l(d,{size:"md",class:"py-3",label:"Ollama URL",description:"URL to server where Ollama is running."},{default:i(()=>[l(r,{modelValue:o(t).settingsMap.ollama_url.value,"onUpdate:modelValue":e[5]||(e[5]=s=>o(t).settingsMap.ollama_url.value=s),placeholder:"Ollama URL",class:"w-full",type:"text",size:"md",autocomplete:"off"},null,8,["modelValue"])]),_:1}),l(d,{size:"md",class:"py-3",label:"Ollama Vision Model",description:"Override Ollama Vision model used by default."},{default:i(()=>[l(r,{modelValue:o(t).settingsMap.ollama_vision_model.value,"onUpdate:modelValue":e[6]||(e[6]=s=>o(t).settingsMap.ollama_vision_model.value=s),placeholder:"Ollama Vision Model",class:"w-full",type:"text",size:"md",autocomplete:"off"},null,8,["modelValue"])]),_:1}),l(d,{size:"md",class:"py-3",label:"Ollama LLM Model",description:"Override Ollama LLM model used by default."},{default:i(()=>[l(r,{modelValue:o(t).settingsMap.ollama_llm_model.value,"onUpdate:modelValue":e[7]||(e[7]=s=>o(t).settingsMap.ollama_llm_model.value=s),placeholder:"Ollama Vision Model",class:"w-full",type:"text",size:"md",autocomplete:"off"},null,8,["modelValue"])]),_:1}),l(d,{size:"md",class:"py-3",label:"Ollama Keepalive",description:"Set Ollama keepalive time (e.g. 30s) for how long the model is kept in memory."},{default:i(()=>[l(r,{modelValue:o(t).settingsMap.ollama_keepalive.value,"onUpdate:modelValue":e[8]||(e[8]=s=>o(t).settingsMap.ollama_keepalive.value=s),placeholder:"Ollama LLM Model",class:"w-full",type:"text",size:"md",autocomplete:"off"},null,8,["modelValue"])]),_:1}),l(g,{class:"mt-3",label:"Prompt translations"}),l(d,{size:"md",class:"py-3",label:"Translations provider",description:"Prompt translations provider. Empty if not enabled."},{default:i(()=>[a("div",Z,[l(b,{modelValue:o(t).settingsMap.translations_provider.value,"onUpdate:modelValue":e[9]||(e[9]=s=>o(t).settingsMap.translations_provider.value=s),color:"white",variant:"outline",placeholder:"Select translations provider",options:o(t).settingsMap.translations_provider.options},null,8,["modelValue","options"]),o(t).settingsMap.translations_provider.value?(c(),y(f,{key:0,icon:"i-heroicons-x-mark",variant:"outline",color:"white",class:"ml-2",onClick:e[10]||(e[10]=()=>o(t).settingsMap.translations_provider.value="")})):v("",!0)])]),_:1})])):v("",!0),o(_).isAdmin?(c(),M("div",ee,[e[20]||(e[20]=a("h4",{class:"mb-3 font-bold"},"Upload Flow",-1)),e[21]||(e[21]=a("p",{class:"text-gray-400 text-sm mb-3"}," Upload a Visionatrix workflow file (.json) to add it to the available flows. On successful upload of the valid workflow file, the installation will start automatically. ",-1)),a("div",te,[l(r,{ref_key:"flowFileInput",ref:x,type:"file",accept:".json",class:"w-auto"},null,512),l(f,{icon:"i-heroicons-arrow-up-tray-16-solid",variant:"outline",loading:o(w),onClick:U},{default:i(()=>e[19]||(e[19]=[u(" Upload Flow ")])),_:1},8,["loading"])])])):v("",!0),a("div",le,[e[23]||(e[23]=a("h3",{class:"mb-3 text-xl font-bold"},"User preferences (overrides global)",-1)),l(d,{size:"md",class:"py-3",label:"Google API key"},{description:i(()=>e[22]||(e[22]=[u(" Google API key, required for Flows, e.g. where ComfyUI-Gemini Node is used. Instruction how to obtain key "),a("a",{class:"hover:underline font-bold",href:"https://ai.google.dev/gemini-api/docs/api-key"},"here",-1),u(". ")])),default:i(()=>[l(r,{modelValue:o(t).settingsMap.google_api_key_user.value,"onUpdate:modelValue":e[11]||(e[11]=s=>o(t).settingsMap.google_api_key_user.value=s),placeholder:"Google API key",class:"w-full",type:"password",icon:"i-heroicons-shield-check",size:"md",autocomplete:"off"},null,8,["modelValue"])]),_:1}),l(g,{class:"mt-3",label:"UI preferences"}),e[24]||(e[24]=a("p",{class:"text-slate text-sm text-orange-300 dark:text-orange-100 text-center"},"Stored in browser local storage",-1)),l(d,{size:"md",class:"py-3",label:"Outputs maximum image size",description:"To keep the output seamless, we limit the size of the outputs (512px by default)."},{default:i(()=>[l(O,{modelValue:o(m).$state.outputMaxSize,"onUpdate:modelValue":e[12]||(e[12]=s=>o(m).$state.outputMaxSize=s),options:["512","768","1024","1536","2048"]},null,8,["modelValue"])]),_:1})]),l(f,{icon:"i-heroicons-check-16-solid",onClick:h},{default:i(()=>e[25]||(e[25]=[u(" Save ")])),_:1})])])]),_:1})}}});export{de as default};