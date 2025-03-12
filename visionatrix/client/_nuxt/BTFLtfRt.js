import{_ as pe}from"./nHx2oaFc.js";import{_ as fe}from"./juZwMdV-.js";import{_ as _e}from"./DqjMivpb.js";import{_ as ge,a as ye}from"./LGfL0kYB.js";import{B as he,C as G,_ as ve,f as N,c as h,o as c,a as g,F as A,r as K,n as z,b as n,D as R,k as v,w as i,i as w,h as Q,t as _,E as j,G as W,H as be,I as J,J as Ue,K as ke,L as Ce,y as X,M as Y,N as k,v as Z,d as y,p as e,O as D,m as ee,P as E,s as H,Q as we,u as Ve,q as Se,g as Me,x as F,A as Ie,j as xe,R as ze}from"./DJTyhk8y.js";import{_ as Be}from"./Dj5JoWNO.js";import{a as $e}from"./BOOO941Y.js";import{_ as te}from"./BOcOQLH-.js";import{_ as Oe,a as Fe}from"./k3sCMvp5.js";const De={wrapper:"relative min-w-0",ol:"flex items-center gap-x-1.5",li:"flex items-center gap-x-1.5 text-gray-500 dark:text-gray-400 text-sm leading-6 min-w-0",base:"flex items-center gap-x-1.5 group font-semibold min-w-0",label:"block truncate",icon:{base:"flex-shrink-0 w-5 h-5",active:"",inactive:""},divider:{base:"flex-shrink-0 w-5 h-5 rtl:rotate-180"},active:"text-primary-500 dark:text-primary-400",inactive:" hover:text-gray-700 dark:hover:text-gray-200",default:{divider:"i-heroicons-chevron-right-20-solid"}},q=he(G.ui.strategy,G.ui.breadcrumb,De),Le=N({components:{UIcon:Q,ULink:W},inheritAttrs:!1,props:{links:{type:Array,default:()=>[]},divider:{type:String,default:()=>q.default.divider},class:{type:[String,Object,Array],default:()=>""},ui:{type:Object,default:()=>({})}},setup(l){const{ui:b,attrs:a}=be("breadcrumb",J(l,"ui"),q,J(l,"class"));return{ui:b,attrs:a,getULinkProps:Ce,twMerge:ke,twJoin:Ue}}}),Re={key:1,role:"presentation"};function Ae(l,b,a,B,C,U){const u=Q,f=W;return c(),h("nav",j({"aria-label":"Breadcrumb",class:l.ui.wrapper},l.attrs),[g("ol",{class:z(l.ui.ol)},[(c(!0),h(A,null,K(l.links,(s,d)=>(c(),h("li",{key:d,class:z(l.ui.li)},[n(f,j({as:"span",class:[l.ui.base,d===l.links.length-1?l.ui.active:s.to?l.ui.inactive:""],"aria-current":d===l.links.length-1?"page":void 0,ref_for:!0},l.getULinkProps(s),{onClick:s.click}),{default:i(()=>[R(l.$slots,"icon",{link:s,index:d,isActive:d===l.links.length-1},()=>[s.icon?(c(),w(u,{key:0,name:s.icon,class:z(l.twMerge(l.twJoin(l.ui.icon.base,d===l.links.length-1?l.ui.icon.active:s.to?l.ui.icon.inactive:""),s.iconClass))},null,8,["name","class"])):v("",!0)]),R(l.$slots,"default",{link:s,index:d,isActive:d===l.links.length-1},()=>[s.label?(c(),h("span",{key:0,class:z(l.twMerge(l.ui.label,s.labelClass))},_(s.label),3)):v("",!0)])]),_:2},1040,["class","aria-current","onClick"]),d<l.links.length-1?R(l.$slots,"divider",{key:0},()=>[l.divider?(c(),h(A,{key:0},[l.divider.startsWith("i-")?(c(),w(u,{key:0,name:l.divider,class:z(l.ui.divider.base),role:"presentation"},null,8,["name","class"])):(c(),h("span",Re,_(l.divider),1))],64)):v("",!0)]):v("",!0)],2))),128))],2)],16)}const Ee=ve(Le,[["render",Ae]]),Ne={class:"orphan-models"},Pe={class:"text-md font-bold"},Te={key:0,class:"text-red-500"},Ge={key:0,class:"flex justify-end items-center space-x-2 mt-3"},je={class:"text-gray-500 text-sm"},Je=["href"],He={key:1},qe={class:"p-4 flex flex-col space-y-2 max-h-60 overflow-y-auto"},Ke={key:2,class:"text-gray-500"},Qe=N({__name:"OrphanModels",setup(l){const b=X();Y(()=>{a()});function a(){b.getOrphanModelsList().then(s=>{console.debug("[DEBUG] Orphan models: ",s),U.value=s})}const B=[{key:"full_path",label:"Path",sortable:!0,class:""},{key:"size",label:"Size",sortable:!0,class:""},{key:"creation_time",label:"Created time",sortable:!0,class:""},{key:"res_model",label:"Model",sortable:!0,class:""},{key:"possible_flows",label:"Possible Flows",sortable:!0,class:""},{key:"actions",label:"Actions",sortable:!1,class:""}];function C(){console.debug("[DEBUG] Deleting orphan models: ",u),f.value=!0,Promise.all(u.value.map(s=>b.deleteOrphanModel(s.full_path,s.creation_time))).then(()=>{a(),f.value=!1,u.value=u.value.filter(s=>s.full_path!==s.full_path)}).catch(s=>{console.error("[ERROR] Failed to delete orphan models: ",s),H().add({title:"Failed to delete orphan models",description:s.details}),f.value=!1})}const U=k([]),u=k([]),f=k(!1);return Z(()=>b.settingsMap.comfyui_models_folder.value,()=>{a()}),(s,d)=>{const I=ee,L=we,x=te;return c(),h("div",Ne,[g("h3",Pe,[d[2]||(d[2]=y(" Orphan models ")),e(U).length>0?(c(),h("span",Te,"("+_(e(U).length)+" - "+_(("formatBytes"in s?s.formatBytes:e(D))(e(U).reduce((r,p)=>r+p.size,0)))+")",1)):v("",!0)]),d[5]||(d[5]=g("p",{class:"text-gray-500 text-sm"}," Orphan models are models that are not associated with any model type. They are not used in any installed flow and can be deleted. ",-1)),e(u).length>0?(c(),h("div",Ge,[g("span",je," Selected: "+_(e(u).length)+" ("+_(("formatBytes"in s?s.formatBytes:e(D))(e(u).reduce((r,p)=>r+p.size,0)))+") ",1),n(I,{icon:"i-heroicons-trash-16-solid",variant:"outline",color:"red",loading:e(f),onClick:d[0]||(d[0]=()=>{C()})},{default:i(()=>d[3]||(d[3]=[y(" Delete selected ")])),_:1},8,["loading"])])):v("",!0),e(U).length>0?(c(),w(x,{key:1,modelValue:e(u),"onUpdate:modelValue":d[1]||(d[1]=r=>E(u)?u.value=r:null),class:"mt-5",ui:{thead:"sticky top-0 dark:bg-gray-800 bg-white z-10"},rows:e(U),columns:B,style:{"max-height":"40vh"}},{"full_path-data":i(({row:r})=>[y(_(r.full_path),1)]),"size-data":i(({row:r})=>[y(_(r.size?("formatBytes"in s?s.formatBytes:e(D))(r.size):"-"),1)]),"creation_time-data":i(({row:r})=>[y(_(r.creation_time?new Date(r.creation_time*1e3).toLocaleString():"-"),1)]),"res_model-data":i(({row:r})=>[r.res_model?(c(),h("a",{key:0,href:r.res_model.homepage,target:"_blank",class:"text-blue-500"},_(r.res_model.name),9,Je)):(c(),h("span",He,"-"))]),"possible_flows-data":i(({row:r})=>[n(L,null,{panel:i(()=>[g("div",qe,[(c(!0),h(A,null,K(r.possible_flows,p=>(c(),w(I,{key:p.id,to:`/workflows/${p==null?void 0:p.name}`,variant:"soft",color:"blue",target:"_blank"},{default:i(()=>[y(_(p.name),1)]),_:2},1032,["to"]))),128))])]),default:i(()=>[n(I,{icon:"i-heroicons-chevron-down-16-solid",variant:"outline",color:"blue"},{default:i(()=>[y(_(r.possible_flows.length),1)]),_:2},1024)]),_:2},1024)]),"actions-data":i(({row:r})=>[n(I,{icon:"i-heroicons-trash-16-solid",variant:"outline",color:"red",loading:e(f),disabled:r.readonly===!0,onClick:()=>{console.debug("[DEBUG] Deleting orphan model: ",r),f.value=!0,e(b).deleteOrphanModel(r.full_path,r.creation_time).then(()=>{a()}).catch(p=>{console.error("[ERROR] Failed to delete orphan model: ",p),("useToast"in s?s.useToast:e(H))().add({title:"Failed to delete orphan model",description:p.details})}).finally(()=>{f.value=!1})}},{default:i(()=>d[4]||(d[4]=[y(" Delete ")])),_:2},1032,["loading","disabled","onClick"])]),_:1},8,["modelValue","rows"])):(c(),h("span",Ke,"No orphan models found."))])}}}),We={class:"flex flex-col md:flex-row"},Xe={class:"px-5 pb-5 md:w-4/5"},Ye={key:0,class:"admin-settings mb-3"},Ze={class:"mt-3 mb-5"},et={class:"p-4 max-h-screen"},tt=["onClick"],ot={class:"flex items-center mt-2"},ct=N({__name:"comfyui",setup(l){Ve({title:"ComfyUI settings - Visionatrix",meta:[{name:"description",content:"ComfyUI settings - Visionatrix"}]});const b=Se(),a=X(),B=Me(),C=k(!1),U=k(!1),u=k([]),f=k(""),s=F(()=>u.value.length===0?[]:f.value===""?Object.keys(u.value).map(m=>{let t=0;return u.value[m].length>0&&(t=u.value[m].reduce((V,S)=>V+(S.total_size??0),0)),{full_path:m,total_size:t,create_time:null}}):u.value[f.value]??[]),d=F(()=>{const m=[{label:"Root",to:""}];if(f.value==="")return m;const t=f.value.split("/");let V="";return t.forEach(S=>{V+=S,m.push({label:S,to:V}),V+="/"}),m}),I=F(()=>{const m=[{key:"full_path",label:"Path",sortable:!0,class:""},{key:"total_size",label:"Size",sortable:!0,class:""}];return f.value!==""&&m.push({key:"create_time",label:"Created time",sortable:!0,class:""}),m});function L(m){m.full_path in u.value&&(f.value=m.full_path)}const x=k(!0);Z(()=>a.localSettings.showComfyUiNavbarButton,()=>{a.saveLocalSettings()});const r=["comfyui_models_folder","comfyui_base_data_folder","comfyui_output_folder","comfyui_input_folder","comfyui_user_folder","remote_vae_flows"],p=k(!1);function P(){p.value=!0,a.saveChanges(r).finally(()=>{p.value=!1})}const oe=F(()=>B.remoteVaeSupportedFlows.map(m=>({label:`${m.display_name} (${m.name})`,value:m.name})));return Y(()=>{a.settingsMap.remote_vae_flows.value&&(a.settingsMap.remote_vae_flows.value=JSON.parse(a.settingsMap.remote_vae_flows.value)??[])}),(m,t)=>{const V=pe,S=fe,T=_e,$=ge,O=ee,M=Be,le=ye,se=$e,ae=xe,ne=Ee,ie=te,re=Oe,de=Fe,ue=Qe,me=Ie;return c(),w(me,{class:"lg:h-dvh"},{default:i(()=>[g("div",We,[n(V,{links:e(a).links,class:"md:w-1/5"},null,8,["links"]),g("div",Xe,[e(b).isAdmin?(c(),h("div",Ye,[t[15]||(t[15]=g("h3",{class:"mb-3 text-xl font-bold"},"ComfyUI settings (global)",-1)),g("div",Ze,[n(S,{class:"my-5"}),n(M,{size:"md",class:"py-3",label:"ComfyUI models folder",description:"Absolute path to the models folders or relative to current Visionatrix folder. Overrides ComfyUI base data folder."},{default:i(()=>[n(T,{class:"mt-3",color:"blue",variant:"solid",title:"ComfyUI settings changes requires server restart",description:"Restart Visionatrix server to apply changes",icon:"i-heroicons-exclamation-triangle"}),n($,{modelValue:e(a).settingsMap.comfyui_models_folder.value,"onUpdate:modelValue":t[0]||(t[0]=o=>e(a).settingsMap.comfyui_models_folder.value=o),placeholder:"ComfyUI folder path",class:"w-fit mr-3 mt-3",type:"text",size:"sm",icon:"i-heroicons-folder-16-solid",loading:e(p),autocomplete:"off"},null,8,["modelValue","loading"]),n(O,{icon:"i-heroicons-eye",class:"mt-3",color:"cyan",onClick:t[1]||(t[1]=()=>{e(a).getComfyUiFolderListing().then(o=>{console.debug("[DEBUG] ComfyUI folders: ",o),u.value=o.folders}),C.value=!0})},{default:i(()=>t[11]||(t[11]=[y(" Show ComfyUI folders ")])),_:1})]),_:1}),n(M,{size:"md",class:"py-3",label:"ComfyUI base data folder",description:"Set the ComfyUI base data directory with an absolute path."},{default:i(()=>[n($,{modelValue:e(a).settingsMap.comfyui_base_data_folder.value,"onUpdate:modelValue":t[2]||(t[2]=o=>e(a).settingsMap.comfyui_base_data_folder.value=o),placeholder:"ComfyUI base data folder path",class:"w-full",type:"text",size:"sm",icon:"i-heroicons-folder-16-solid",loading:e(p),autocomplete:"off"},null,8,["modelValue","loading"])]),_:1}),n(M,{size:"md",class:"py-3",label:"ComfyUI output folder",description:"Set the ComfyUI output directory with an absolute path. Overrides ComfyUI base data folder."},{default:i(()=>[n($,{modelValue:e(a).settingsMap.comfyui_output_folder.value,"onUpdate:modelValue":t[3]||(t[3]=o=>e(a).settingsMap.comfyui_output_folder.value=o),placeholder:"ComfyUI output folder path",class:"w-full",type:"text",size:"sm",icon:"i-heroicons-folder-16-solid",loading:e(p),autocomplete:"off"},null,8,["modelValue","loading"])]),_:1}),n(M,{size:"md",class:"py-3",label:"ComfyUI input folder",description:"Set the ComfyUI input directory with an absolute path. Overrides ComfyUI base data folder."},{default:i(()=>[n($,{modelValue:e(a).settingsMap.comfyui_input_folder.value,"onUpdate:modelValue":t[4]||(t[4]=o=>e(a).settingsMap.comfyui_input_folder.value=o),placeholder:"ComfyUI input folder path",class:"w-full",type:"text",size:"sm",icon:"i-heroicons-folder-16-solid",loading:e(p),autocomplete:"off"},null,8,["modelValue","loading"])]),_:1}),n(M,{size:"md",class:"py-3",label:"ComfyUI user folder",description:"Set the ComfyUI user directory with an absolute path. Overrides ComfyUI base data folder."},{default:i(()=>[n($,{modelValue:e(a).settingsMap.comfyui_user_folder.value,"onUpdate:modelValue":t[5]||(t[5]=o=>e(a).settingsMap.comfyui_user_folder.value=o),placeholder:"ComfyUI user folder path",class:"w-full",type:"text",size:"sm",icon:"i-heroicons-folder-16-solid",loading:e(p),autocomplete:"off"},null,8,["modelValue","loading"])]),_:1}),n(S,{class:"my-5"}),n(M,{size:"md",label:"VAE Remote Decoding",description:"List of installed Flows for which 'VAE Remote Decoding' is enabled"},{default:i(()=>[e(B).remoteVaeSupportedFlows.length===0?(c(),w(T,{key:0,variant:"soft",color:"teal",class:"my-3",title:"No Flows with VAE Remote Decoding support installed",icon:"i-heroicons-information-circle"})):v("",!0),n(le,{modelValue:e(a).settingsMap.remote_vae_flows.value,"onUpdate:modelValue":t[6]||(t[6]=o=>e(a).settingsMap.remote_vae_flows.value=o),options:e(oe),"value-attribute":"value",class:"flex h-10",multiple:"",searchable:"",placeholder:"Select flows to allow remote VAE decoding"},null,8,["modelValue","options"])]),_:1}),n(O,{class:"mt-3",icon:"i-heroicons-check-16-solid",loading:e(p),onClick:P},{default:i(()=>t[12]||(t[12]=[y(" Save ")])),_:1},8,["loading"]),e(a).settingsMap.comfyui_models_folder.value!==""?(c(),w(re,{key:0,modelValue:e(C),"onUpdate:modelValue":t[9]||(t[9]=o=>E(C)?C.value=o:null),class:"z-[90]",fullscreen:""},{default:i(()=>[n(O,{class:"absolute top-4 right-4",icon:"i-heroicons-x-mark",variant:"ghost",onClick:t[7]||(t[7]=()=>C.value=!1)}),g("div",et,[t[13]||(t[13]=g("h3",{class:"text-xl text-center"},"ComfyUI folders",-1)),g("div",null,[n(se,{modelValue:e(x),"onUpdate:modelValue":t[8]||(t[8]=o=>E(x)?x.value=o:null),class:"mt-3",label:"Hide empty folders"},null,8,["modelValue"])]),n(ne,{links:e(d),class:"my-2"},{default:i(({link:o,isActive:ce})=>[n(ae,{color:ce?"primary":"gray",class:"rounded-full truncate cursor-pointer select-none",onClick:()=>{f.value=o.to}},{default:i(()=>[y(_(o.label),1)]),_:2},1032,["color","onClick"])]),_:1},8,["links"]),n(ie,{loading:e(U),"loading-state":{icon:"i-heroicons-arrow-path-20-solid",label:"Loading..."},rows:e(s).filter(o=>e(x)?o.total_size>0:!0),columns:e(I),style:{"max-height":"80vh"}},{"full_path-data":i(({row:o})=>[g("span",{class:z({"text-blue-500":o.full_path in e(u),"cursor-pointer":o.full_path in e(u)}),onClick:()=>L(o)},_(o.full_path),11,tt)]),"total_size-data":i(({row:o})=>[y(_(o.total_size?("formatBytes"in m?m.formatBytes:e(D))(o.total_size):"-"),1)]),"create_time-data":i(({row:o})=>[y(_(o.create_time&&new Date(o.create_time).getTime()!==0?new Date(o.create_time).toLocaleString():"-"),1)]),_:1},8,["loading","rows","columns"])])]),_:1},8,["modelValue"])):v("",!0)]),e(a).isNextcloudIntegration?v("",!0):(c(),w(M,{key:0,size:"md",class:"py-3",label:"Show 'Open ComfyUI' navbar button",description:"Toggle Navbar button to open ComfyUI in a new tab (Stored in browser local storage	)"},{default:i(()=>[g("div",ot,[n(de,{modelValue:e(a).localSettings.showComfyUiNavbarButton,"onUpdate:modelValue":t[10]||(t[10]=o=>e(a).localSettings.showComfyUiNavbarButton=o),class:"mr-3"},null,8,["modelValue"]),n(O,{icon:"i-heroicons-rectangle-group-16-solid",variant:"outline",color:"white",to:("buildBackendUrl"in m?m.buildBackendUrl:e(ze))()+"/comfy/",target:"_blank"},{default:i(()=>t[14]||(t[14]=[y(" Open ComfyUI ")])),_:1},8,["to"])])]),_:1})),n(ue,{class:"mt-3"})])):v("",!0)])])]),_:1})}}});export{ct as default};
