import{_ as Q}from"./DN8K9I2q.js";import{_ as Y}from"./CSI9-IcW.js";import{_ as Z}from"./m7-puyJG.js";import{f as E,u as K,z as X,y as ee,V as te,W as oe,N as k,v as W,g as ae,x as y,M as se,i as M,w as a,A as le,o as _,a as m,b as l,p as s,c as O,k as re,P as w,t as r,l as ne,m as ie,d as n,O as f,Q as de,F as ue,r as me,j as ce,G as _e,s as R}from"./DUTaT_LT.js";import{_ as fe}from"./D1Cp61OB.js";import"./CW-7P0AM.js";import"./CsF2FcnR.js";const pe={class:"flex flex-col md:flex-row"},ve={class:"px-5 md:w-4/5"},ke={class:"flex flex-col lg:flex-row px-3 py-3.5 border-b border-gray-200 dark:border-gray-700"},be={class:"flex"},ge={key:0,class:"flex flex-col md:flex-row items-center"},ye={key:0},we={class:"p-4 flex flex-wrap max-w-64 max-h-60 overflow-y-auto"},Ae=E({__name:"workers",setup(xe){K({title:"Workers - Visionatrix",meta:[{name:"description",content:"Workers - Visionatrix"}]});const c=X(),L=ee();te(()=>{c.startPolling()}),oe(()=>{c.stopPolling()});const x=[{id:"worker_status",label:"Worker status",sortable:!0},{id:"federated",label:"Federated",sortable:!0},{id:"busy",label:"Busy",sortable:!0},{id:"worker_id",label:"Worker ID"},{id:"worker_version",label:"Worker version",sortable:!0},{id:"last_seen",label:"Last seen",sortable:!0},{id:"tasks_to_give",label:"Tasks to give",sortable:!1},{id:"os",label:"OS",sortable:!0},{id:"version",label:"Python Version",sortable:!0},{id:"device_name",label:"Device name"},{id:"device_type",label:"Device type",sortable:!0},{id:"vram_total",label:"VRAM total",sortable:!0},{id:"vram_free",label:"VRAM free",sortable:!0},{id:"torch_vram_total",label:"Torch VRAM total",sortable:!0},{id:"torch_vram_free",label:"Torch VRAM free",sortable:!0},{id:"ram_total",label:"RAM total",sortable:!0},{id:"ram_free",label:"RAM free",sortable:!0}],b=x.map(e=>({key:e.id,label:e.label,sortable:e.sortable||!1,class:""})),D=localStorage.getItem("selectedColumns");let h=null;if(D!==null){const e=JSON.parse(D);h=b.filter(o=>e.includes(o.key)),h.sort(F)}const p=k(h||[...b]);W(p,e=>{localStorage.setItem("selectedColumns",JSON.stringify(Object.values(b).filter(o=>e.includes(o)).map(o=>o.key))),e.sort(F)});function F(e,o){return x.findIndex(i=>i.id===e.key)-x.findIndex(i=>i.id===o.key)}const V=ae(),T=y(()=>V.flows.map(e=>({label:e.display_name,value:e.name}))),d=k([]);se(()=>{if(V.flows.length===0){V.fetchFlows().then(()=>{d.value=[...T.value]});return}d.value=[...T.value]});const I=y(()=>d.value.length===0?"All":d.value.length),B=k(!1);function G(){B.value=!0,Promise.all(u.value.filter(e=>e.federated_instance_name==="").map(e=>c.setTasksToGive(e.worker_id,d.value.map(o=>o.value)))).then(()=>{R().add({title:"Tasks to give updated",description:"Tasks to give updated successfully"}),u.value=[]}).catch(()=>{R().add({title:"Failed to update tasks to give",description:"Try again"})}).finally(()=>{B.value=!1,c.loadWorkers()})}const v=k(""),S=y(()=>c.$state.workers),P=y(()=>S.value.filter(e=>Object.values(e).some(o=>String(o).toLowerCase().includes(v.value.toLowerCase()))));function N(e){const o=new Date(e.last_seen.includes("Z")?e.last_seen:e.last_seen+"Z");return new Date().getTime()-o.getTime()<=60*5*1e3?"Online":"Offline"}const u=k([]);return W(S,e=>{if(u.value.length>0){const o=u.value.map(i=>i.worker_id);u.value=e.filter(i=>o.includes(i.worker_id))}}),(e,o)=>{const i=Q,C=Y,$=Z,U=ie,j=ne,g=ce,z=_e,q=de,H=fe,J=le;return _(),M(J,{class:"lg:h-dvh"},{default:a(()=>[m("div",pe,[l(i,{links:s(L).links,class:"md:w-1/5"},null,8,["links"]),m("div",ve,[o[6]||(o[6]=m("h2",{class:"mb-3 text-xl"},"Workers",-1)),m("div",ke,[m("div",be,[l(C,{modelValue:s(p),"onUpdate:modelValue":o[0]||(o[0]=t=>w(p)?p.value=t:null),class:"mr-3",options:s(b),multiple:""},null,8,["modelValue","options"]),l($,{modelValue:s(v),"onUpdate:modelValue":o[1]||(o[1]=t=>w(v)?v.value=t:null),placeholder:"Filter workers..."},null,8,["modelValue"])]),s(u).length>=1?(_(),O("div",ge,[l(C,{modelValue:s(d),"onUpdate:modelValue":o[2]||(o[2]=t=>w(d)?d.value=t:null),searchable:"",class:"mr-3 my-3 lg:mx-3 lg:my-0 w-full max-w-64 min-w-64",options:s(T),multiple:""},{label:a(()=>[m("span",null,"Tasks to give ("+r(s(I))+")",1)]),_:1},8,["modelValue","options"]),l(j,{text:"Flows available for worker to get tasks"},{default:a(()=>[l(U,{icon:"i-heroicons-check-16-solid",variant:"outline",color:"cyan",size:"sm",loading:s(B),onClick:G},{default:a(()=>o[5]||(o[5]=[n(" Update tasks to give ")])),_:1},8,["loading"])]),_:1}),l(U,{icon:"i-heroicons-x-mark",variant:"outline",color:"white",class:"ml-2",onClick:o[3]||(o[3]=()=>{d.value=[]})})])):re("",!0)]),l(H,{modelValue:s(u),"onUpdate:modelValue":o[4]||(o[4]=t=>w(u)?u.value=t:null),columns:s(p),rows:s(v)===""?s(S):s(P),loading:s(c).$state.loading},{"worker_status-data":a(({row:t})=>[l(g,{variant:"solid",color:N(t)==="Online"?"green":"red"},{default:a(()=>[n(r(N(t)),1)]),_:2},1032,["color"])]),"federated-data":a(({row:t})=>[l(g,{variant:"solid",color:t.federated_instance_name!==""?"blue":"green"},{default:a(()=>[n(r(t.federated_instance_name!==""?"Yes":"No"),1)]),_:2},1032,["color"])]),"busy-data":a(({row:t})=>[l(g,{variant:"solid",color:t.empty_task_requests_count===0?"red":"green"},{default:a(()=>[n(r(t.empty_task_requests_count===0?"Yes":"No"),1)]),_:2},1032,["color"])]),"tasks_to_give-data":a(({row:t})=>[t.tasks_to_give.length===0?(_(),O("span",ye,"All")):(_(),M(q,{key:1,popper:{placement:"bottom"}},{panel:a(()=>[m("div",we,[(_(!0),O(ue,null,me(t.tasks_to_give,A=>(_(),M(g,{key:A,class:"mr-2 mb-2",variant:"solid",color:"cyan"},{default:a(()=>[l(z,{class:"hover:underline",to:`/workflows/${A}`},{default:a(()=>[n(r(A),1)]),_:2},1032,["to"])]),_:2},1024))),128))])]),default:a(()=>[l(U,{icon:"i-heroicons-list-bullet-16-solid",variant:"outline",color:"gray",size:"sm"},{default:a(()=>[m("span",null,r(t.tasks_to_give.length)+" selected",1)]),_:2},1024)]),_:2},1024))]),"last_seen-data":a(({row:t})=>[n(r(new Date(t.last_seen).toLocaleString()),1)]),"vram_total-data":a(({row:t})=>[n(r(("formatBytes"in e?e.formatBytes:s(f))(t.vram_total)),1)]),"vram_free-data":a(({row:t})=>[n(r(("formatBytes"in e?e.formatBytes:s(f))(t.vram_free)),1)]),"torch_vram_total-data":a(({row:t})=>[n(r(("formatBytes"in e?e.formatBytes:s(f))(t.torch_vram_total)),1)]),"torch_vram_free-data":a(({row:t})=>[n(r(("formatBytes"in e?e.formatBytes:s(f))(t.torch_vram_free)),1)]),"ram_total-data":a(({row:t})=>[n(r(("formatBytes"in e?e.formatBytes:s(f))(t.ram_total)),1)]),"ram_free-data":a(({row:t})=>[n(r(("formatBytes"in e?e.formatBytes:s(f))(t.ram_free)),1)]),_:1},8,["modelValue","columns","rows","loading"])])])]),_:1})}}});export{Ae as default};
