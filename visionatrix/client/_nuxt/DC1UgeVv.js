import{_ as G}from"./R9xmvNDd.js";import{_ as ce,o,c as i,a as u,s as b,q as s,t as S,l as p,b as D,v as h,F as V,r as U,i as $,k as H,h as Q,S as P,d as pe,f as fe,y as ge,z as q,A as ye,B as L,K as f,T,U as z,V as R,W as K}from"./DWQ3q0v-.js";import{_ as X}from"./Bwdp9M5L.js";const me={wrapper:"relative overflow-x-auto",base:"min-w-full table-fixed",divide:"divide-y divide-gray-300 dark:divide-gray-700",thead:"relative",tbody:"divide-y divide-gray-200 dark:divide-gray-800",caption:"sr-only",tr:{base:"",selected:"bg-gray-50 dark:bg-gray-800/50",expanded:"bg-gray-50 dark:bg-gray-800/50",active:"hover:bg-gray-50 dark:hover:bg-gray-800/50 cursor-pointer"},th:{base:"text-left rtl:text-right",padding:"px-4 py-3.5",color:"text-gray-900 dark:text-white",font:"font-semibold",size:"text-sm"},td:{base:"whitespace-nowrap",padding:"px-4 py-4",color:"text-gray-500 dark:text-gray-400",font:"",size:"text-sm"},checkbox:{padding:"ps-4"},loadingState:{wrapper:"flex flex-col items-center justify-center flex-1 px-6 py-14 sm:px-14",label:"text-sm text-center text-gray-900 dark:text-white",icon:"w-6 h-6 mx-auto text-gray-400 dark:text-gray-500 mb-4 animate-spin"},emptyState:{wrapper:"flex flex-col items-center justify-center flex-1 px-6 py-14 sm:px-14",label:"text-sm text-center text-gray-900 dark:text-white",icon:"w-6 h-6 mx-auto text-gray-400 dark:text-gray-500 mb-4"},expand:{icon:"transform transition-transform duration-200"},progress:{wrapper:"absolute inset-x-0 -bottom-[0.5px] p-0"},default:{sortAscIcon:"i-heroicons-bars-arrow-up-20-solid",sortDescIcon:"i-heroicons-bars-arrow-down-20-solid",sortButton:{icon:"i-heroicons-arrows-up-down-20-solid",trailing:!0,square:!0,color:"gray",variant:"ghost",class:"-m-1.5"},expandButton:{icon:"i-heroicons-chevron-down",color:"gray",variant:"ghost",size:"xs",class:"-my-1.5 align-middle"},checkbox:{color:"primary"},progress:{color:"primary",animation:"carousel"},loadingState:{icon:"i-heroicons-arrow-path-20-solid",label:"Loading..."},emptyState:{icon:"i-heroicons-circle-stack-20-solid",label:"No items."}}};function be(e){return e?e[0].toUpperCase()+e.slice(1):""}const m=ye(L.ui.strategy,L.ui.table,me);function he(e,c){return JSON.stringify(e)===JSON.stringify(c)}function W(e,c,v){return e===c?0:v==="asc"?e<c?-1:1:e>c?-1:1}const ve=fe({components:{UIcon:Q,UButton:H,UProgress:X,UCheckbox:G},inheritAttrs:!1,props:{modelValue:{type:Array,default:null},by:{type:[String,Function],default:()=>he},rows:{type:Array,default:()=>[]},columns:{type:Array,default:null},columnAttribute:{type:String,default:"label"},sort:{type:Object,default:()=>({})},sortMode:{type:String,default:"auto"},sortButton:{type:Object,default:()=>m.default.sortButton},sortAscIcon:{type:String,default:()=>m.default.sortAscIcon},sortDescIcon:{type:String,default:()=>m.default.sortDescIcon},expandButton:{type:Object,default:()=>m.default.expandButton},expand:{type:Object,default:()=>null},loading:{type:Boolean,default:!1},loadingState:{type:Object,default:()=>m.default.loadingState},emptyState:{type:Object,default:()=>m.default.emptyState},caption:{type:String,default:null},progress:{type:Object,default:()=>m.default.progress},class:{type:[String,Object,Array],default:()=>""},ui:{type:Object,default:()=>({})},multipleExpand:{type:Boolean,default:!0}},emits:["update:modelValue","update:sort","update:expand"],setup(e,{emit:c,attrs:v}){const{ui:C,attrs:N}=ge("table",q(e,"ui"),m,q(e,"class")),O=f(()=>e.columns??Object.keys(e.rows[0]??{}).map(t=>({key:t,label:be(t),sortable:!1,class:void 0,sort:W}))),l=T(e,"sort",c,{passive:!0,defaultValue:z({},e.sort,{column:null,direction:"asc"})}),g=T(e,"expand",c,{passive:!0,defaultValue:z({},e.expand,{openedRows:[],row:null})}),j={column:l.value.column,direction:null},w=f(()=>{var d;if(!((d=l.value)!=null&&d.column)||e.sortMode==="manual")return e.rows;const{column:t,direction:n}=l.value;return e.rows.slice().sort((I,ie)=>{var J;const re=R(I,t),ue=R(ie,t);return(((J=O.value.find(de=>de.key===t))==null?void 0:J.sort)??W)(re,ue,n)})}),a=f({get(){return e.modelValue},set(t){c("update:modelValue",t)}}),y=t=>new Set(t.map(n=>JSON.stringify(n))),r=f(()=>e.rows.length),k=f(()=>{const t=y(a.value),n=y(e.rows);return Array.from(t).filter(d=>n.has(d)).length}),B=f(()=>!a.value||!e.rows?!1:k.value>0&&k.value<r.value),E=f(()=>k.value===r.value),Y=f(()=>e.emptyState===null?null:{...C.value.default.emptyState,...e.emptyState}),Z=f(()=>e.loadingState===null?null:{...C.value.default.loadingState,...e.loadingState});function A(t,n){if(typeof e.by=="string"){const d=x(e.by);return d(t)===d(n)}return e.by(t,n)}function x(t){return n=>R(n,t)}function F(t){return e.modelValue?a.value.some(n=>A(K(n),K(t))):!1}function _(t){if(l.value.column===t.key){const n=!t.direction||t.direction==="asc"?"desc":"asc";l.value.direction===n?l.value=z({},j,{column:null,direction:"asc"}):l.value={column:l.value.column,direction:l.value.direction==="asc"?"desc":"asc"}}else l.value={column:t.key,direction:t.direction||"asc"}}function ee(t){v.onSelect&&v.onSelect(t)}function te(){const t=[...a.value];e.rows.forEach(n=>{F(n)||t.push(n)}),a.value=t}function ae(t){t?te():a.value=[]}function ne(t,n){if(t)a.value.push(n);else{const d=a.value.findIndex(I=>A(I,n));a.value.splice(d,1)}}function oe(t,n,d=""){return R(t,n,d)}function M(t){var n;return(n=g.value)!=null&&n.openedRows?g.value.openedRows.some(d=>A(d,t)):!1}function se(t){g.value={openedRows:M(t)?g.value.openedRows.filter(n=>!A(n,t)):e.multipleExpand?[...g.value.openedRows,t]:[t],row:t}}function le(t){if(t.sortable){if(l.value.column!==t.key)return"none";if(l.value.direction==="asc")return"ascending";if(l.value.direction==="desc")return"descending"}}return{ui:C,attrs:N,sort:l,columns:O,rows:w,selected:a,indeterminate:B,emptyState:Y,loadingState:Z,isAllRowChecked:E,onChangeCheckbox:ne,isSelected:F,onSort:_,onSelect:ee,onChange:ae,getRowData:oe,toggleOpened:se,getAriaSort:le,isExpanded:M}}}),ke=["aria-sort"],Se={key:1},Ce={key:0},we={key:0},Be=["colspan"],Ae={key:1},Ve=["colspan"],$e=["onClick"],Re={key:0},Oe={colspan:"100%"};function je(e,c,v,C,N,O){const l=G,g=H,j=X,w=Q;return o(),i("div",h({class:e.ui.wrapper},e.attrs),[u("table",{class:s([e.ui.base,e.ui.divide])},[e.$slots.caption||e.caption?b(e.$slots,"caption",{key:0},()=>[u("caption",{class:s(e.ui.caption)},S(e.caption),3)]):p("",!0),u("thead",{class:s(e.ui.thead)},[u("tr",{class:s(e.ui.tr.base)},[e.modelValue?(o(),i("th",{key:0,scope:"col",class:s(e.ui.checkbox.padding)},[D(l,h({"model-value":e.isAllRowChecked,indeterminate:e.indeterminate},e.ui.default.checkbox,{"aria-label":"Select all",onChange:e.onChange}),null,16,["model-value","indeterminate","onChange"])],2)):p("",!0),e.expand?(o(),i("th",{key:1,scope:"col",class:s(e.ui.tr.base)},c[0]||(c[0]=[u("span",{class:"sr-only"},"Expand",-1)]),2)):p("",!0),(o(!0),i(V,null,U(e.columns,(a,y)=>(o(),i("th",{key:y,scope:"col",class:s([e.ui.th.base,e.ui.th.padding,e.ui.th.color,e.ui.th.font,e.ui.th.size,a.class]),"aria-sort":e.getAriaSort(a)},[b(e.$slots,`${a.key}-header`,{column:a,sort:e.sort,onSort:e.onSort},()=>[a.sortable?(o(),$(g,h({key:0,ref_for:!0},{...e.ui.default.sortButton||{},...e.sortButton},{icon:!e.sort.column||e.sort.column!==a.key?e.sortButton.icon||e.ui.default.sortButton.icon:e.sort.direction==="asc"?e.sortAscIcon:e.sortDescIcon,label:a[e.columnAttribute],onClick:r=>e.onSort(a)}),null,16,["icon","label","onClick"])):(o(),i("span",Se,S(a[e.columnAttribute]),1))])],10,ke))),128))],2),e.loading&&e.progress?(o(),i("tr",Ce,[u("td",{colspan:0,class:s(e.ui.progress.wrapper)},[D(j,h({...e.ui.default.progress||{},...e.progress},{size:"2xs"}),null,16)],2)])):p("",!0)],2),u("tbody",{class:s(e.ui.tbody)},[e.loadingState&&e.loading&&!e.rows.length?(o(),i("tr",we,[u("td",{colspan:e.columns.length+(e.modelValue?1:0)+(e.expand?1:0)},[b(e.$slots,"loading-state",{},()=>[u("div",{class:s(e.ui.loadingState.wrapper)},[e.loadingState.icon?(o(),$(w,{key:0,name:e.loadingState.icon,class:s(e.ui.loadingState.icon),"aria-hidden":"true"},null,8,["name","class"])):p("",!0),u("p",{class:s(e.ui.loadingState.label)},S(e.loadingState.label),3)],2)])],8,Be)])):e.emptyState&&!e.rows.length?(o(),i("tr",Ae,[u("td",{colspan:e.columns.length+(e.modelValue?1:0)+(e.expand?1:0)},[b(e.$slots,"empty-state",{},()=>[u("div",{class:s(e.ui.emptyState.wrapper)},[e.emptyState.icon?(o(),$(w,{key:0,name:e.emptyState.icon,class:s(e.ui.emptyState.icon),"aria-hidden":"true"},null,8,["name","class"])):p("",!0),u("p",{class:s(e.ui.emptyState.label)},S(e.emptyState.label),3)],2)])],8,Ve)])):(o(!0),i(V,{key:2},U(e.rows,(a,y)=>(o(),i(V,{key:y},[u("tr",{class:s([e.ui.tr.base,e.isSelected(a)&&e.ui.tr.selected,e.isExpanded(a)&&e.ui.tr.expanded,e.$attrs.onSelect&&e.ui.tr.active,a==null?void 0:a.class]),onClick:()=>e.onSelect(a)},[e.modelValue?(o(),i("td",{key:0,class:s(e.ui.checkbox.padding)},[D(l,h({"model-value":e.isSelected(a),ref_for:!0},e.ui.default.checkbox,{"aria-label":"Select row",onChange:r=>e.onChangeCheckbox(r,a),onClickCapture:P(()=>e.onSelect(a),["stop"])}),null,16,["model-value","onChange","onClickCapture"])],2)):p("",!0),e.expand?(o(),i("td",{key:1,class:s([e.ui.td.base,e.ui.td.padding,e.ui.td.color,e.ui.td.font,e.ui.td.size])},[e.$slots["expand-action"]?b(e.$slots,"expand-action",{key:0,row:a,isExpanded:e.isExpanded(a),toggle:()=>e.toggleOpened(a)}):(o(),$(g,h({key:1,disabled:a.disabledExpand,ref_for:!0},{...e.ui.default.expandButton||{},...e.expandButton},{ui:{icon:{base:[e.ui.expand.icon,e.isExpanded(a)&&"rotate-180"].join(" ")}},onClickCapture:P(r=>e.toggleOpened(a),["stop"])}),null,16,["disabled","ui","onClickCapture"]))],2)):p("",!0),(o(!0),i(V,null,U(e.columns,(r,k)=>{var B;return o(),i("td",{key:k,class:s([e.ui.td.base,e.ui.td.padding,e.ui.td.color,e.ui.td.font,e.ui.td.size,r==null?void 0:r.rowClass,(B=a[r.key])==null?void 0:B.class])},[b(e.$slots,`${r.key}-data`,{column:r,row:a,index:y,getRowData:E=>e.getRowData(a,r.key,E)},()=>[pe(S(e.getRowData(a,r.key)),1)])],2)}),128))],10,$e),e.isExpanded(a)?(o(),i("tr",Re,[u("td",Oe,[b(e.$slots,"expand",{row:a,index:y})])])):p("",!0)],64))),128))],2)],2)],16)}const ze=ce(ve,[["render",je]]);export{ze as _};
