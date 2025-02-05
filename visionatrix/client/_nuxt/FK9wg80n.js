import{_ as T,a as W}from"./BIHBmI1B.js";import{_ as q}from"./BTyr5pyh.js";import{_ as I,a as D,b as P}from"./CZJqnhts.js";import{_ as E}from"./DMdrGPwt.js";import{f as L,g as F,c,o as l,b as n,w as i,a,t as p,d as k,h as R,i as m,F as z,r as M,j as G,k as $,l as H,m as O,n as N,p as t,u as J,q as K,s as Q,v as j,x as A,y as X,z as Y}from"./B2vMKEpe.js";import{_ as Z}from"./DZxF8G6u.js";const ee={class:"p-4 w-full md:w-6/12 lg:w-4/12 z-[10]"},te={class:"flex flex-grow justify-between"},oe=["title"],se={class:"flex flex-col items-between text-sm"},le=["title"],ne={class:"flex flex-row flex-wrap items-center mb-2"},ae={class:"flex flex-row items-center"},ie=["href"],re={class:"flex flex-row items-center mb-2"},fe=["href"],ce={key:1},me={class:"flex flex-row items-center mb-2"},de={class:"flex flex-row items-center"},_e=L({__name:"ListItem",props:{flow:{type:Object,required:!0}},setup(o){const e=F();return(B,s)=>{const f=R,u=H,b=O,C=G,r=I;return l(),c("div",ee,[n(r,{as:"div",class:"hover:shadow-md"},{header:i(()=>{var d,x,g;return[a("div",te,[a("h2",{class:"text-xl font-bold truncate flex items-center",title:(d=o.flow)==null?void 0:d.display_name},[(x=o.flow)!=null&&x.private?(l(),m(u,{key:0,text:"This flow is local, manually added"},{default:i(()=>[n(f,{name:"i-heroicons-lock-closed",class:N(["mr-2",{"text-stone-500":!o.flow.is_supported_by_workers}])},null,8,["class"])]),_:1})):$("",!0),n(u,{text:o.flow.is_supported_by_workers?"":"No workers capable of running this flow",popper:{placement:"top"}},{default:i(()=>{var w;return[a("span",{class:N({"text-stone-500":!o.flow.is_supported_by_workers})},p((w=o.flow)==null?void 0:w.display_name),3)]}),_:1},8,["text"])],8,oe),t(e).isFlowInstalled((g=o.flow)==null?void 0:g.name)?(l(),m(u,{key:0,text:"Mark flow as favorite",class:"ml-3",popper:{placement:"top"},"open-delay":500},{default:i(()=>[n(b,{icon:t(e).isFlowFavorite(o.flow.name)?"i-heroicons-star-16-solid":"i-heroicons-star",variant:"outline",color:"yellow",onClick:s[0]||(s[0]=w=>t(e).markFlowFavorite(o.flow))},null,8,["icon"])]),_:1})):$("",!0)])]}),footer:i(()=>{var d;return[n(b,{to:`/workflows/${(d=o.flow)==null?void 0:d.name}`,icon:"i-heroicons-arrow-up-right-16-solid",class:"flex justify-center dark:bg-slate-500 bg-slate-500 dark:hover:bg-slate-700 hover:bg-slate-700 dark:text-white"},{default:i(()=>s[9]||(s[9]=[k(" Open ")])),_:1},8,["to"])]}),default:i(()=>{var d,x,g,w,y,v,S,V,U;return[a("div",se,[a("p",{class:"text-md text-slate-400 truncate text-ellipsis mb-2",title:(d=o.flow)==null?void 0:d.description},p((x=o.flow)==null?void 0:x.description),9,le),a("p",ne,[a("span",ae,[n(f,{name:"i-heroicons-user-16-solid",class:"mr-1"}),s[1]||(s[1]=a("b",null,"Author:",-1)),s[2]||(s[2]=k("  "))]),a("a",{class:"hover:underline flex flex-row items-center",href:(g=o.flow)==null?void 0:g.homepage,rel:"noopener",target:"_blank"},p((w=o.flow)==null?void 0:w.author),9,ie)]),a("p",re,[n(f,{name:"i-heroicons-document-text",class:"mr-1"}),(y=o.flow)!=null&&y.documentation?(l(),c("a",{key:0,class:"hover:underline",href:(v=o.flow)==null?void 0:v.documentation,rel:"noopener",target:"_blank"},"Documentation",8,fe)):(l(),c("span",ce,"No documentation"))]),a("p",me,[n(f,{name:"i-heroicons-tag",class:"mr-1"}),s[3]||(s[3]=a("b",null,"Tags:",-1)),s[4]||(s[4]=k("  ")),((S=o.flow)==null?void 0:S.tags.length)>0?(l(!0),c(z,{key:0},M((V=o.flow)==null?void 0:V.tags,h=>(l(),m(C,{key:h,label:h,color:"white",variant:"solid",class:"m-1"},null,8,["label"]))),128)):(l(),m(C,{key:1,label:"No tags",color:"white",variant:"solid",class:"m-1"}))]),a("p",de,[n(f,{name:"i-mdi-help-network-outline",class:"mr-1"}),s[7]||(s[7]=a("b",null,"Platforms:",-1)),s[8]||(s[8]=k("  ")),n(u,{text:"Linux"},{default:i(()=>[n(f,{name:"i-mdi-linux",class:"mr-1"})]),_:1}),n(u,{text:"Microsoft Windows"},{default:i(()=>[n(f,{name:"i-mdi-microsoft-windows",class:"mr-1"})]),_:1}),o.flow.is_macos_supported?(l(),m(u,{key:0,text:"macOS"},{default:i(()=>[n(f,{name:"i-mdi-apple",class:"mr-1"})]),_:1})):$("",!0),(U=o.flow)!=null&&U.required_memory_gb?(l(),m(u,{key:1,class:"flex flex-row items-center",text:"Required VRAM memory (GB)"},{default:i(()=>{var h;return[s[5]||(s[5]=k(" (")),n(f,{name:"i-mdi-memory",class:"mr-1"}),a("span",null,p((h=o.flow)==null?void 0:h.required_memory_gb)+" GB",1),s[6]||(s[6]=k(") "))]}),_:1})):$("",!0)])])]}),_:1})])}}}),ue={class:"w-full sticky z-[100] top-1 flex flex-col md:flex-row justify-center items-center my-1"},we={class:"flex"},pe={key:0,class:"truncate"},xe={key:1},ge={key:0},he={key:1,class:"flex flex-wrap justify-center items-center mb-10"},ke={key:2,class:"text-center text-slate-500 my-5"},Ue=L({__name:"index",setup(o){J({title:"Workflows - Visionatrix",meta:[{name:"description",content:"Workflows - Visionatrix"}]});const e=F(),B=K();Q(()=>e.paginatedFlows,()=>{e.flows.length<=e.$state.pageSize?e.$state.page=1:e.$state.page>Math.ceil(e.flows.length/e.$state.pageSize)&&(e.$state.page=Math.ceil(e.flows.length/e.$state.pageSize))});function s(){return[[{label:"Show unsupported flows",icon:e.$state.show_unsupported_flows?"i-mdi-filter-check":"i-mdi-filter-minus",slot:"show_unsupported_flows",click:()=>{e.$state.show_unsupported_flows=!e.$state.show_unsupported_flows,e.saveUserOptions()}}],[{label:"Clear filters",labelClass:"text-xs",icon:"i-mdi-filter-off",iconClass:"w-4 h-4",click:()=>{e.$state.flows_search_filter="",e.$state.flows_tags_filter=[],e.$state.show_unsupported_flows=!1}}]]}const f=j(()=>e.$state.flows_search_filter||e.$state.flows_tags_filter.length>0||e.$state.show_unsupported_flows),u=j(()=>(e.$state.flows_search_filter?1:0)+e.$state.flows_tags_filter.length+(e.$state.show_unsupported_flows?1:0));function b(){B.clear(),A().loadLocalSettings(),A().fetchAllSettings(),F().fetchFlows(),X().loadWorkers()}return(C,r)=>{const d=T,x=q,g=D,w=E,y=O,v=W,S=P,V=Z,U=_e,h=Y;return l(),m(h,{class:"lg:h-dvh"},{default:i(()=>[t(e).$state.loading.flows_available||t(e).loading.flows_installed||t(e).$state.loading.tasks_history?(l(),m(d,{key:0})):(l(),c(z,{key:1},[a("div",ue,[n(x,{modelValue:t(e).$state.flows_search_filter,"onUpdate:modelValue":r[0]||(r[0]=_=>t(e).$state.flows_search_filter=_),icon:"i-heroicons-magnifying-glass-20-solid",color:"white",class:"mb-1 md:mr-3 md:mb-0",label:"Filter by prompt",trailing:!0,placeholder:"Search flows"},null,8,["modelValue"]),t(e).flows.length>t(e).$state.pageSize?(l(),m(g,{key:0,modelValue:t(e).$state.page,"onUpdate:modelValue":r[1]||(r[1]=_=>t(e).$state.page=_),class:"mb-1 md:mr-3 md:mb-0","page-count":t(e).$state.pageSize,total:t(e).flows.length},null,8,["modelValue","page-count","total"])):$("",!0),a("div",we,[n(w,{modelValue:t(e).$state.flows_tags_filter,"onUpdate:modelValue":r[2]||(r[2]=_=>t(e).$state.flows_tags_filter=_),options:t(e).flowsTags,multiple:"",searchable:""},{label:i(()=>[t(e).$state.flows_tags_filter.length>0?(l(),c("span",pe,p(t(e).$state.flows_tags_filter.join(",")),1)):(l(),c("span",xe,"Select tags to filter"))]),_:1},8,["modelValue","options"]),n(S,{class:"ml-2",items:s(),mode:"click",label:"Options"},{show_unsupported_flows:i(()=>[n(v,{modelValue:t(e).$state.show_unsupported_flows,"onUpdate:modelValue":r[3]||(r[3]=_=>t(e).$state.show_unsupported_flows=_)},null,8,["modelValue"]),r[4]||(r[4]=a("span",{class:"text-xs"},"Show unsupported flows",-1))]),default:i(()=>[n(y,{color:"white",icon:"i-mdi-filter"},{default:i(()=>[a("span",null,p(t(e).flows.length),1),t(f)?(l(),c("span",ge,"("+p(t(u))+")",1)):$("",!0)]),_:1})]),_:1},8,["items"])])]),t(e).$state.error.flows_available||t(e).$state.error.flows_installed?(l(),m(V,{key:0,class:"my-4",title:"Error fetching flows",icon:"i-mdi-alert-circle",description:"An error occurred while fetching flows. Please try again later.",variant:"soft",color:"red"},{actions:i(()=>[n(y,{icon:"i-heroicons-arrow-path-solid",variant:"outline",color:"white",onClick:b},{default:i(()=>r[5]||(r[5]=[k(" Retry ")])),_:1})]),_:1})):$("",!0),t(e).flows.length>0?(l(),c("div",he,[(l(!0),c(z,null,M(t(e).paginatedFlows,_=>(l(),m(U,{key:_.name,flow:_},null,8,["flow"]))),128))])):(l(),c("p",ke,p(t(e).$state.flows_search_filter||t(e).$state.flows_tags_filter?"No flows found":"No flows available"),1))],64))]),_:1})}}});export{Ue as default};
