import{_ as T}from"./CFcARYUe.js";import{S as A,T as I,U as L,f as M,u as D,q as O,y as z,V as H,W as J,x as q,N as x,v as F,i as G,w as t,A as W,o as h,a as c,b as a,p as o,c as Y,k as K,m as Q,d as r,t as w,j as X,P as U}from"./DLc8_Hx0.js";import{_ as Z}from"./DuFDpVa3.js";import{_ as ee}from"./B4Tjgb3G.js";import{_ as ne}from"./Ch0YXI_h.js";import{a as te}from"./Bkr4qq1k.js";import{_ as ae}from"./wK_zZ8Rc.js";import"./C2xnmzxy.js";const le=A("federatedStore",{state:()=>({loading:!1,instances:[],interval:null}),actions:{async loadFederationInstances(){const{$apiFetch:l}=I();return this.loading=!0,await l("/federation/instances").then(i=>{this.instances=i}).finally(()=>{this.loading=!1})},startPolling(){this.loadFederationInstances(),this.interval=L(()=>{this.loadFederationInstances()},3e3)},stopPolling(){clearInterval(this.interval)},registerFederationInstance(l){const{$apiFetch:i}=I();return i("/federation/instance",{method:"POST",body:JSON.stringify({instance_name:l.instance_name,url_address:l.url_address,username:l.username,password:l.password,enabled:l.enabled})})},updateFederationInstance(l){const{$apiFetch:i}=I();return i(`/federation/instance?instance_name=${l.instance_name}`,{method:"PUT",body:JSON.stringify({url_address:l.url_address,username:l.username,password:l.password,enabled:l.enabled})})},deleteFederationInstance(l){const{$apiFetch:i}=I();return i(`/federation/instance?instance_name=${l}`,{method:"DELETE"}).then(()=>{this.loadFederationInstances()})}}}),se={class:"flex flex-col md:flex-row"},oe={class:"px-5 pb-5 md:w-4/5"},de={key:0,class:"admin-settings mb-3"},re={class:"flex items-center gap-2"},ie={class:"p-4 overflow-y-auto"},ue={class:"font-bold"},ce={class:"flex flex-col gap-2 mt-3"},me={class:"flex justify-end mt-3"},ye=M({__name:"federated",setup(l){D({title:"Federated settings - Visionatrix",meta:[{name:"description",content:"Federated settings - Visionatrix"}]});const i=O(),k=z(),m=le();H(()=>{m.startPolling()}),J(()=>{m.stopPolling()});const S=[{id:"instance_name",label:"Instance name",sortable:!0},{id:"url_address",label:"URL address",sortable:!0},{id:"username",label:"Username",sortable:!0},{id:"enabled",label:"Enabled",sortable:!0},{id:"created_at",label:"Created at",sortable:!0},{id:"actions",label:"Actions",sortable:!1}].map(s=>({key:s.id,label:s.label,sortable:s.sortable,class:""})),C=q(()=>m.$state.instances),u=x(!1),d=x(null),_=x(""),f=x(""),p=x(""),v=x(""),b=x(!1);F(u,s=>{s||(_.value="",f.value="",p.value="",v.value="",b.value=!1),d.value&&!s&&(d.value=null)}),F(d,s=>{s!==null&&(_.value=s.instance_name,f.value=s.url_address,p.value=s.username,v.value=s.password,b.value=s.enabled)});function E(){d.value!==null?m.updateFederationInstance({...d.value,instance_name:_.value,url_address:f.value,username:p.value,password:v.value,enabled:b.value}).then(()=>{u.value=!1,d.value=null}):m.registerFederationInstance({instance_name:_.value,url_address:f.value,username:p.value,password:v.value,enabled:b.value}).then(()=>{m.loadFederationInstances(),u.value=!1})}return(s,e)=>{const N=T,y=Q,P=X,R=Z,V=ee,g=ne,$=te,j=ae,B=W;return h(),G(B,{class:"lg:h-dvh"},{default:t(()=>[c("div",se,[a(N,{links:o(k).links,class:"md:w-1/5"},null,8,["links"]),c("div",oe,[o(i).isAdmin?(h(),Y("div",de,[e[12]||(e[12]=c("h3",{class:"mb-3 text-xl font-bold"},"Federated settings",-1)),a(g,{size:"md",class:"py-3",label:"Federated instances"},{default:t(()=>[a(y,{class:"my-3",variant:"outline",icon:"i-heroicons-plus-16-solid",color:"cyan",onClick:e[0]||(e[0]=()=>{u.value=!0})},{default:t(()=>e[8]||(e[8]=[r(" Register new instance ")])),_:1}),a(R,{columns:o(S),rows:o(C)},{"instance_name-data":t(({row:n})=>[r(w(n.instance_name),1)]),"url_address-data":t(({row:n})=>[r(w(n.url_address),1)]),"username-data":t(({row:n})=>[r(w(n.username),1)]),"enabled-data":t(({row:n})=>[a(P,{variant:"soft",color:n.enabled?"green":"red"},{default:t(()=>[r(w(n.enabled?"Yes":"No"),1)]),_:2},1032,["color"])]),"created_at-data":t(({row:n})=>[r(w(new Date(n.created_at).toLocaleString()),1)]),"actions-data":t(({row:n})=>[c("div",re,[a(y,{icon:"i-heroicons-pencil-16-solid",variant:"outline",color:"cyan",size:"sm",onClick:()=>{d.value={...n},u.value=!0}},{default:t(()=>e[9]||(e[9]=[r(" Edit ")])),_:2},1032,["onClick"]),a(y,{icon:"i-heroicons-trash-16-solid",variant:"outline",color:"red",size:"sm",onClick:()=>{o(m).deleteFederationInstance(n.instance_name)}},{default:t(()=>e[10]||(e[10]=[r(" Delete ")])),_:2},1032,["onClick"])])]),_:1},8,["columns","rows"]),a(j,{modelValue:o(u),"onUpdate:modelValue":e[7]||(e[7]=n=>U(u)?u.value=n:null)},{default:t(()=>[c("div",ie,[c("h2",ue,w(o(d)!==null?"Edit instance":"Register new instance"),1),c("div",ce,[a(g,{label:"Instance name",class:"flex justify-center flex-col w-full"},{default:t(()=>[a(V,{modelValue:o(_),"onUpdate:modelValue":e[1]||(e[1]=n=>U(_)?_.value=n:null),type:"text",placeholder:"Instance name"},null,8,["modelValue"])]),_:1}),a(g,{label:"URL address",class:"flex justify-center flex-col w-full"},{default:t(()=>[a(V,{modelValue:o(f),"onUpdate:modelValue":e[2]||(e[2]=n=>U(f)?f.value=n:null),type:"text",placeholder:"URL address"},null,8,["modelValue"])]),_:1}),a(g,{label:"Username",class:"flex justify-center flex-col w-full"},{default:t(()=>[a(V,{modelValue:o(p),"onUpdate:modelValue":e[3]||(e[3]=n=>U(p)?p.value=n:null),type:"text",placeholder:"Username"},null,8,["modelValue"])]),_:1}),a(g,{label:"Password",class:"flex justify-center flex-col w-full"},{default:t(()=>[a(V,{modelValue:o(v),"onUpdate:modelValue":e[4]||(e[4]=n=>U(v)?v.value=n:null),type:"password",placeholder:"Password",autocomplete:"off"},null,8,["modelValue"])]),_:1}),a(g,{label:"Enabled",class:"flex justify-center flex-col w-full"},{default:t(()=>[a($,{modelValue:o(b),"onUpdate:modelValue":e[5]||(e[5]=n=>U(b)?b.value=n:null),label:o(d)!==null?"Enabled":"Enable after register"},null,8,["modelValue","label"])]),_:1})]),c("div",me,[a(y,{class:"mr-2",variant:"soft",color:"white",onClick:e[6]||(e[6]=()=>{u.value=!1})},{default:t(()=>e[11]||(e[11]=[r(" Cancel ")])),_:1}),a(y,{variant:"solid",color:"cyan",onClick:E},{default:t(()=>[r(w(o(d)!==null?"Update":"Register"),1)]),_:1})])])]),_:1},8,["modelValue"])]),_:1})])):K("",!0)])])]),_:1})}}});export{ye as default};
