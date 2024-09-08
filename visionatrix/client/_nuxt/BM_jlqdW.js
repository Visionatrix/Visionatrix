import{_ as z}from"./Bud1W4sB.js";import{f as F,u as A,q as G,s as I,v as O,g as P,x as v,n as C,h as N,w as n,p as $,o as f,a,b as t,j as l,c as x,d as _,i as y,k as q,l as B}from"./BvRzgVOS.js";import{_ as j,a as E}from"./D6QeYp77.js";import{_ as H}from"./StEd8U7R.js";const L={class:"flex flex-col md:flex-row"},R={class:"px-5 pb-5 md:w-4/5"},T={key:0,class:"admin-settings mb-3"},D={class:"flex items-center"},W={key:1,class:"upload-flow mb-5 py-4 rounded-md"},J={class:"flex items-center space-x-3"},K={class:"user-settings mb-3"},oe=F({__name:"index",setup(Q){A({title:"Settings - Visionatrix",meta:[{name:"description",content:"Settings - Visionatrix"}]});const h=[{label:"Settings",icon:"i-heroicons-cog-6-tooth-20-solid",to:"/settings"},{label:"Workers information",icon:"i-heroicons-chart-bar-16-solid",to:"/settings/workers"}],m=G(),o=I(),r=O();function k(){console.debug("Saving settings",o.settingsMap),Promise.all(Object.keys(o.settingsMap).map(i=>o.settingsMap[i].admin&&m.isAdmin?o.saveGlobalSetting(o.settingsMap[i].key,o.settingsMap[i].value,o.settingsMap[i].sensitive):o.saveUserSetting(o.settingsMap[i].key,o.settingsMap[i].value))).then(()=>{r.add({title:"Settings saved",description:"Settings saved successfully"})}).catch(i=>{r.add({title:"Error saving setting",description:i.message})})}const p=P(),c=v(null),g=v(!1);function b(){const i=c.value.$refs.input.files[0]||null;if(!i){r.add({title:"No file selected",description:"Please select a file to upload"});return}g.value=!0,p.uploadFlow(i).then(e=>{if(console.debug("uploadFlow",e),e&&"detail"in e&&(e==null?void 0:e.detail)!==""){r.add({title:"Error uploading flow",description:e.detail});return}else r.add({title:"Flow uploaded",description:"Flow uploaded successfully"});c.value.$refs.input.value=""}).catch(e=>{console.debug("uploadFlow error",e),r.add({title:"Error uploading flow",description:e.message})}).finally(()=>{g.value=!1})}return C(()=>p.outputMaxSize,()=>{p.saveUserOptions()}),(i,e)=>{const V=z,M=q,d=j,u=H,w=B,U=E,S=$;return f(),N(S,{class:"lg:h-dvh"},{default:n(()=>[a("div",L,[t(V,{links:h,class:"md:w-1/5"}),a("div",R,[e[14]||(e[14]=a("h2",{class:"mb-3 text-xl"},"Settings",-1)),l(m).isAdmin?(f(),x("div",T,[e[8]||(e[8]=a("h3",{class:"mb-3"},"Admin settings",-1)),a("div",D,[t(M,{name:"i-heroicons-question-mark-circle",class:"mr-2 text-amber-400"}),e[7]||(e[7]=a("p",{class:"text-amber-400"},[a("span",null,"Access tokens are required for "),a("a",{class:"hover:underline underline-offset-4",href:"https://visionatrix.github.io/VixFlowsDocs/GatedModels.html",target:"_blank"},"gated models"),_(". ")],-1))]),t(u,{size:"md",class:"py-3",label:"Huggingface Auth token",description:"Bearer authentication token from your Huggingface account to allow downloading gated models with limited access"},{default:n(()=>[t(d,{modelValue:l(o).settingsMap.huggingface_auth_token.value,"onUpdate:modelValue":e[0]||(e[0]=s=>l(o).settingsMap.huggingface_auth_token.value=s),placeholder:"Huggingface Auth token",class:"w-full",type:"password",icon:"i-heroicons-shield-check",size:"md",autocomplete:"off"},null,8,["modelValue"])]),_:1}),t(u,{size:"md",class:"py-3",label:"Google API key",description:"Global Google API key, required for Flows, e.g. where ComfyUI-Gemini Node is used"},{default:n(()=>[t(d,{modelValue:l(o).settingsMap.google_api_key.value,"onUpdate:modelValue":e[1]||(e[1]=s=>l(o).settingsMap.google_api_key.value=s),placeholder:"Google API key",class:"w-full",type:"password",icon:"i-heroicons-shield-check",size:"md",autocomplete:"off"},null,8,["modelValue"])]),_:1}),t(u,{size:"md",class:"py-3",label:"Proxy",description:"Proxy configuration string (to access Gemini)"},{default:n(()=>[t(d,{modelValue:l(o).settingsMap.google_proxy.value,"onUpdate:modelValue":e[2]||(e[2]=s=>l(o).settingsMap.google_proxy.value=s),placeholder:"Proxy",class:"w-full",type:"text",size:"md",autocomplete:"off"},null,8,["modelValue"])]),_:1}),t(u,{size:"md",class:"py-3",label:"Ollama URL",description:"URL to server where Ollama is running, required for flows using node with it"},{default:n(()=>[t(d,{modelValue:l(o).settingsMap.ollama_url.value,"onUpdate:modelValue":e[3]||(e[3]=s=>l(o).settingsMap.ollama_url.value=s),placeholder:"Ollama URL",class:"w-full",type:"text",size:"md",autocomplete:"off"},null,8,["modelValue"])]),_:1}),t(u,{size:"md",class:"py-3",label:"Ollama Vision Model",description:"Override Ollama Vision model used in workflows by default"},{default:n(()=>[t(d,{modelValue:l(o).settingsMap.ollama_vision_model.value,"onUpdate:modelValue":e[4]||(e[4]=s=>l(o).settingsMap.ollama_vision_model.value=s),placeholder:"Ollama Vision Model",class:"w-full",type:"text",size:"md",autocomplete:"off"},null,8,["modelValue"])]),_:1})])):y("",!0),l(m).isAdmin?(f(),x("div",W,[e[10]||(e[10]=a("h3",{class:"mb-3 text-xl font-bold"},"Upload Flow",-1)),e[11]||(e[11]=a("p",{class:"text-gray-400 text-sm mb-3"}," Upload a Visionatrix workflow file (.json) to add it to the available flows. On successful upload of the valid workflow file, the installation will start automatically. ",-1)),a("div",J,[t(d,{ref_key:"flowFileInput",ref:c,type:"file",accept:".json",class:"w-auto"},null,512),t(w,{icon:"i-heroicons-arrow-up-tray-16-solid",variant:"outline",loading:l(g),onClick:b},{default:n(()=>e[9]||(e[9]=[_(" Upload Flow ")])),_:1},8,["loading"])])])):y("",!0),a("div",K,[e[12]||(e[12]=a("h3",{class:"mb-3"},"User settings",-1)),t(u,{size:"md",class:"py-3",label:"Google API key",description:"Google API key, required for Flows where, e.g. ComfyUI-Gemini Node is used"},{default:n(()=>[t(d,{modelValue:l(o).settingsMap.google_api_key_user.value,"onUpdate:modelValue":e[5]||(e[5]=s=>l(o).settingsMap.google_api_key_user.value=s),placeholder:"Google API key",class:"w-full",type:"password",icon:"i-heroicons-shield-check",size:"md",autocomplete:"off"},null,8,["modelValue"])]),_:1}),t(u,{size:"md",class:"py-3",label:"Outputs maximum image size",description:"To keep the output seamless, we limit the size of the outputs (512px by default)"},{default:n(()=>[t(U,{modelValue:l(p).$state.outputMaxSize,"onUpdate:modelValue":e[6]||(e[6]=s=>l(p).$state.outputMaxSize=s),options:["512","768","1024","1536","2048"]},null,8,["modelValue"])]),_:1})]),t(w,{icon:"i-heroicons-check-16-solid",onClick:k},{default:n(()=>e[13]||(e[13]=[_(" Save ")])),_:1})])])]),_:1})}}});export{oe as default};
