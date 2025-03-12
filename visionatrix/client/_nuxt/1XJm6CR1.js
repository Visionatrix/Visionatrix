import{_ as Q}from"./nHx2oaFc.js";import{a as Z,_ as E}from"./LGfL0kYB.js";import{f as K,u as q,z as X,y as Y,S as ee,T as te,N as k,v as W,g as oe,x as U,M as se,i as C,w as a,A as ae,o as _,a as d,b as n,p as s,c as D,k as le,P as b,l as ne,m as re,d as r,t as i,O as f,Q as ie,F as ue,r as de,j as me,G as ce,s as I}from"./DJTyhk8y.js";import{_ as _e}from"./BOcOQLH-.js";import"./juZwMdV-.js";import"./BOOO941Y.js";const fe={class:"flex flex-col md:flex-row"},pe={class:"px-5 md:w-4/5"},ve={class:"flex flex-col lg:flex-row px-3 py-3.5 border-b border-gray-200 dark:border-gray-700"},ke={class:"flex"},ge={key:0,class:"flex flex-col md:flex-row items-center"},be={key:0},ye={class:"p-4 flex flex-wrap max-w-64 max-h-60 overflow-y-auto"},Ue=K({__name:"workers",setup(we){q({title:"Workers - Visionatrix",meta:[{name:"description",content:"Workers - Visionatrix"}]});const m=X(),N=Y();ee(()=>{m.startPolling()}),te(()=>{m.stopPolling()});const y=[{id:"worker_status",label:"Worker status",sortable:!0},{id:"id",label:"ID"},{id:"worker_id",label:"Worker ID"},{id:"worker_version",label:"Worker version",sortable:!0},{id:"last_seen",label:"Last seen",sortable:!0},{id:"tasks_to_give",label:"Tasks to give",sortable:!1},{id:"os",label:"OS",sortable:!0},{id:"version",label:"Python Version",sortable:!0},{id:"device_name",label:"Device name"},{id:"device_type",label:"Device type",sortable:!0},{id:"vram_total",label:"VRAM total",sortable:!0},{id:"vram_free",label:"VRAM free",sortable:!0},{id:"torch_vram_total",label:"Torch VRAM total",sortable:!0},{id:"torch_vram_free",label:"Torch VRAM free",sortable:!0},{id:"ram_total",label:"RAM total",sortable:!0},{id:"ram_free",label:"RAM free",sortable:!0}],g=y.map(e=>({key:e.id,label:e.label,sortable:e.sortable||!1,class:""})),M=localStorage.getItem("selectedColumns");let w=null;if(M!==null){const e=JSON.parse(M);w=g.filter(t=>e.includes(t.key)),w.sort(O)}const p=k(w||[...g]);W(p,e=>{localStorage.setItem("selectedColumns",JSON.stringify(Object.values(g).filter(t=>e.includes(t)).map(t=>t.key))),e.sort(O)});function O(e,t){return y.findIndex(l=>l.id===e.key)-y.findIndex(l=>l.id===t.key)}const x=oe(),V=U(()=>x.flows.map(e=>({label:e.display_name,value:e.name}))),c=k([]);se(()=>{if(x.flows.length===0){x.fetchFlows().then(()=>{c.value=[...V.value]});return}c.value=[...V.value]});const T=k(!1);function L(){T.value=!0,Promise.all(u.value.map(e=>m.setTasksToGive(e.worker_id,c.value.map(t=>t.value)))).then(()=>{I().add({title:"Tasks to give updated",description:"Tasks to give updated successfully"}),u.value=[]}).catch(()=>{I().add({title:"Failed to update tasks to give",description:"Try again"})}).finally(()=>{T.value=!1,m.loadWorkers()})}const v=k(""),S=U(()=>m.$state.workers),P=U(()=>S.value.filter(e=>Object.values(e).some(t=>String(t).toLowerCase().includes(v.value.toLowerCase()))));function A(e){const t=new Date(e.last_seen.includes("Z")?e.last_seen:e.last_seen+"Z");return new Date().getTime()-t.getTime()<=60*5*1e3?"Online":"Offline"}const u=k([]);return W(S,e=>{if(u.value.length>0){const t=u.value.map(l=>l.id);u.value=e.filter(l=>t.includes(l.id))}}),(e,t)=>{const l=Q,h=Z,$=E,F=re,G=ne,R=me,j=ce,z=ie,H=_e,J=ae;return _(),C(J,{class:"lg:h-dvh"},{default:a(()=>[d("div",fe,[n(l,{links:s(N).links,class:"md:w-1/5"},null,8,["links"]),d("div",pe,[t[6]||(t[6]=d("h2",{class:"mb-3 text-xl"},"Workers",-1)),d("div",ve,[d("div",ke,[n(h,{modelValue:s(p),"onUpdate:modelValue":t[0]||(t[0]=o=>b(p)?p.value=o:null),class:"mr-3",options:s(g),multiple:""},null,8,["modelValue","options"]),n($,{modelValue:s(v),"onUpdate:modelValue":t[1]||(t[1]=o=>b(v)?v.value=o:null),placeholder:"Filter workers..."},null,8,["modelValue"])]),s(u).length>=1?(_(),D("div",ge,[n(h,{modelValue:s(c),"onUpdate:modelValue":t[2]||(t[2]=o=>b(c)?c.value=o:null),class:"mr-3 my-3 lg:mx-3 lg:my-0 w-full max-w-64 min-w-64",options:s(V),multiple:""},{label:a(()=>t[4]||(t[4]=[d("span",null,"Tasks to give",-1)])),_:1},8,["modelValue","options"]),n(G,{text:"Flows available for worker to get tasks"},{default:a(()=>[n(F,{icon:"i-heroicons-check-16-solid",variant:"outline",color:"cyan",size:"sm",loading:s(T),onClick:L},{default:a(()=>t[5]||(t[5]=[r(" Update tasks to give ")])),_:1},8,["loading"])]),_:1})])):le("",!0)]),n(H,{modelValue:s(u),"onUpdate:modelValue":t[3]||(t[3]=o=>b(u)?u.value=o:null),columns:s(p),rows:s(v)===""?s(S):s(P),loading:s(m).$state.loading},{"worker_status-data":a(({row:o})=>[n(R,{variant:"solid",color:A(o)==="Online"?"green":"red"},{default:a(()=>[r(i(A(o)),1)]),_:2},1032,["color"])]),"tasks_to_give-data":a(({row:o})=>[o.tasks_to_give.length===0?(_(),D("span",be,"All")):(_(),C(z,{key:1,popper:{placement:"bottom"}},{panel:a(()=>[d("div",ye,[(_(!0),D(ue,null,de(o.tasks_to_give,B=>(_(),C(R,{key:B,class:"mr-2 mb-2",variant:"solid",color:"cyan"},{default:a(()=>[n(j,{class:"hover:underline",to:`/workflows/${B}`},{default:a(()=>[r(i(B),1)]),_:2},1032,["to"])]),_:2},1024))),128))])]),default:a(()=>[n(F,{icon:"i-heroicons-list-bullet-16-solid",variant:"outline",color:"gray",size:"sm"},{default:a(()=>[d("span",null,i(o.tasks_to_give.length)+" selected",1)]),_:2},1024)]),_:2},1024))]),"last_seen-data":a(({row:o})=>[r(i(new Date(o.last_seen).toLocaleString()),1)]),"vram_total-data":a(({row:o})=>[r(i(("formatBytes"in e?e.formatBytes:s(f))(o.vram_total)),1)]),"vram_free-data":a(({row:o})=>[r(i(("formatBytes"in e?e.formatBytes:s(f))(o.vram_free)),1)]),"torch_vram_total-data":a(({row:o})=>[r(i(("formatBytes"in e?e.formatBytes:s(f))(o.torch_vram_total)),1)]),"torch_vram_free-data":a(({row:o})=>[r(i(("formatBytes"in e?e.formatBytes:s(f))(o.torch_vram_free)),1)]),"ram_total-data":a(({row:o})=>[r(i(("formatBytes"in e?e.formatBytes:s(f))(o.ram_total)),1)]),"ram_free-data":a(({row:o})=>[r(i(("formatBytes"in e?e.formatBytes:s(f))(o.ram_free)),1)]),_:1},8,["modelValue","columns","rows","loading"])])])]),_:1})}}});export{Ue as default};
