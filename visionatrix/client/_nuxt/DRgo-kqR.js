import{_ as D}from"./DN8K9I2q.js";import{S as z,T as I,U as H,f as J,u as G,q as W,y as Y,s as K,V as Q,W as X,x as E,N as p,v as S,i as Z,w as l,A as ee,o as N,a as v,b as s,p as t,c as te,k as ae,m as ne,d as m,t as x,j as le,P as h}from"./DUTaT_LT.js";import{_ as se}from"./D1Cp61OB.js";import{_ as oe}from"./m7-puyJG.js";import{_ as re}from"./B7zl9-ai.js";import{a as de}from"./CsF2FcnR.js";import{_ as ie}from"./BdIpt8hb.js";import"./CW-7P0AM.js";const ue=z("federatedStore",{state:()=>({loading:!1,instances:[],interval:null}),actions:{async loadFederationInstances(){const{$apiFetch:o}=I();return this.loading=!0,await o("/federation/instances").then(f=>{this.instances=f}).finally(()=>{this.loading=!1})},startPolling(){this.loadFederationInstances(),this.interval=H(()=>{this.loadFederationInstances()},3e3)},stopPolling(){clearInterval(this.interval)},registerFederationInstance(o){const{$apiFetch:f}=I();return f("/federation/instance",{method:"POST",body:JSON.stringify({instance_name:o.instance_name,url_address:o.url_address,username:o.username,password:o.password,enabled:o.enabled})})},updateFederationInstance(o){const{$apiFetch:f}=I();return f(`/federation/instance?instance_name=${o.instance_name}`,{method:"PUT",body:JSON.stringify({url_address:o.url_address,username:o.username,password:o.password,enabled:o.enabled})})},deleteFederationInstance(o){const{$apiFetch:f}=I();return f(`/federation/instance?instance_name=${o}`,{method:"DELETE"}).then(()=>{this.loadFederationInstances()})}}}),ce={class:"flex flex-col md:flex-row"},me={class:"px-5 pb-5 md:w-4/5"},fe={key:0,class:"admin-settings mb-3"},_e={class:"flex items-center gap-2"},pe={class:"p-4 overflow-y-auto"},ve={class:"font-bold"},be={class:"flex flex-col gap-2 mt-3"},ge={class:"flex justify-end mt-3"},Ce=J({__name:"federated",setup(o){G({title:"Federated settings - Visionatrix",meta:[{name:"description",content:"Federated settings - Visionatrix"}]});const f=W(),P=Y(),b=ue(),F=K();Q(()=>{b.startPolling()}),X(()=>{b.stopPolling()});const R=[{id:"actions",label:"Actions",sortable:!1},{id:"instance_name",label:"Instance name",sortable:!0},{id:"url_address",label:"URL address",sortable:!0},{id:"username",label:"Username",sortable:!0},{id:"enabled",label:"Enabled",sortable:!0},{id:"created_at",label:"Created at",sortable:!0}].map(n=>({key:n.id,label:n.label,sortable:n.sortable,class:""})),$=E(()=>b.$state.instances),_=p(!1),k=p(!1),r=p(null),d=p(""),i=p(""),u=p(""),c=p(""),g=p(!1);S(_,n=>{n||(d.value="",i.value="",u.value="",c.value="",g.value=!1),r.value&&!n&&(r.value=null)}),S(r,n=>{n!==null&&(d.value=n.instance_name,i.value=n.url_address,u.value=n.username,c.value=n.password,g.value=n.enabled)});const j=E(()=>d.value.length>0&&i.value.length>0&&u.value.length>0&&c.value.length>0),y=p(!1);function B(){y.value=!0,r.value!==null?b.updateFederationInstance({...r.value,instance_name:d.value,url_address:i.value,username:u.value,password:c.value,enabled:g.value}).then(()=>{_.value=!1,r.value=null}).catch(n=>{console.error(n),F.add({title:"Error",description:n.details?n.details:"Failed to update federated instance. Check console for more details."})}).finally(()=>{y.value=!1}):b.registerFederationInstance({instance_name:d.value,url_address:i.value,username:u.value,password:c.value,enabled:g.value}).then(()=>{b.loadFederationInstances(),_.value=!1}).catch(n=>{console.error(n),F.add({title:"Error",description:n.details?n.details:"Failed to register new federated instance. Check console for more details."})}).finally(()=>{y.value=!1})}return(n,e)=>{const L=D,U=ne,T=le,q=se,V=oe,w=re,A=de,M=ie,O=ee;return N(),Z(O,{class:"lg:h-dvh"},{default:l(()=>[v("div",ce,[s(L,{links:t(P).links,class:"md:w-1/5"},null,8,["links"]),v("div",me,[t(f).isAdmin?(N(),te("div",fe,[e[12]||(e[12]=v("h3",{class:"mb-3 text-xl font-bold"},"Federated settings",-1)),s(w,{size:"md",class:"py-3",label:"Federated instances"},{default:l(()=>[s(U,{class:"my-3",variant:"outline",icon:"i-heroicons-plus-16-solid",color:"cyan",onClick:e[0]||(e[0]=()=>{_.value=!0})},{default:l(()=>e[8]||(e[8]=[m(" Register new instance ")])),_:1}),s(q,{columns:t(R),rows:t($)},{"instance_name-data":l(({row:a})=>[m(x(a.instance_name),1)]),"url_address-data":l(({row:a})=>[m(x(a.url_address),1)]),"username-data":l(({row:a})=>[m(x(a.username),1)]),"enabled-data":l(({row:a})=>[s(T,{variant:"soft",color:a.enabled?"green":"red"},{default:l(()=>[m(x(a.enabled?"Yes":"No"),1)]),_:2},1032,["color"])]),"created_at-data":l(({row:a})=>[m(x(new Date(a.created_at).toLocaleString()),1)]),"actions-data":l(({row:a})=>[v("div",_e,[s(U,{icon:"i-heroicons-pencil-16-solid",variant:"outline",color:"cyan",size:"sm",onClick:()=>{r.value={...a},_.value=!0}},{default:l(()=>e[9]||(e[9]=[m(" Edit ")])),_:2},1032,["onClick"]),s(U,{icon:"i-heroicons-trash-16-solid",variant:"outline",color:"red",size:"sm",loading:t(k),onClick:()=>{k.value=!0,t(b).deleteFederationInstance(a.instance_name).catch(C=>{console.error(C),t(F).add({title:"Error",description:C.details?C.details:"Failed to delete federated instance. Check console for more details."})}).finally(()=>{k.value=!1})}},{default:l(()=>e[10]||(e[10]=[m(" Delete ")])),_:2},1032,["loading","onClick"])])]),_:1},8,["columns","rows"]),s(M,{modelValue:t(_),"onUpdate:modelValue":e[7]||(e[7]=a=>h(_)?_.value=a:null),transition:!1},{default:l(()=>[v("div",pe,[v("h2",ve,x(t(r)!==null?"Edit instance":"Register new instance"),1),v("div",be,[s(w,{label:"Instance name",class:"flex justify-center flex-col w-full",error:!t(d)||t(d).length===0?"Instance name is required":""},{default:l(()=>[s(V,{modelValue:t(d),"onUpdate:modelValue":e[1]||(e[1]=a=>h(d)?d.value=a:null),type:"text",placeholder:"Instance name"},null,8,["modelValue"])]),_:1},8,["error"]),s(w,{label:"URL address",class:"flex justify-center flex-col w-full",error:!t(i)||t(i).length===0?"URL address is required":""},{default:l(()=>[s(V,{modelValue:t(i),"onUpdate:modelValue":e[2]||(e[2]=a=>h(i)?i.value=a:null),type:"text",placeholder:"URL address"},null,8,["modelValue"])]),_:1},8,["error"]),s(w,{label:"Username",class:"flex justify-center flex-col w-full",error:!t(u)||t(u).length===0?"Username is required":""},{default:l(()=>[s(V,{modelValue:t(u),"onUpdate:modelValue":e[3]||(e[3]=a=>h(u)?u.value=a:null),type:"text",placeholder:"Username"},null,8,["modelValue"])]),_:1},8,["error"]),s(w,{label:"Password",class:"flex justify-center flex-col w-full",error:!t(c)||t(c).length===0?"Password is required":""},{default:l(()=>[s(V,{modelValue:t(c),"onUpdate:modelValue":e[4]||(e[4]=a=>h(c)?c.value=a:null),type:"password",placeholder:"Password",autocomplete:"off"},null,8,["modelValue"])]),_:1},8,["error"]),s(w,{label:"Enabled",class:"flex justify-center flex-col w-full"},{default:l(()=>[s(A,{modelValue:t(g),"onUpdate:modelValue":e[5]||(e[5]=a=>h(g)?g.value=a:null),label:t(r)!==null?"Enabled":"Enable after register"},null,8,["modelValue","label"])]),_:1})]),v("div",ge,[s(U,{class:"mr-2",variant:"soft",color:"white",onClick:e[6]||(e[6]=()=>{_.value=!1})},{default:l(()=>e[11]||(e[11]=[m(" Cancel ")])),_:1}),s(U,{variant:"solid",color:"cyan",loading:t(y),disabled:!t(j),onClick:B},{default:l(()=>[m(x(t(r)!==null?"Update":"Register"),1)]),_:1},8,["loading","disabled"])])])]),_:1},8,["modelValue"])]),_:1})])):ae("",!0)])])]),_:1})}}});export{Ce as default};
