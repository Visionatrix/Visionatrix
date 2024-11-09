import{z as L,A as y,_ as T,f as D,B as J,C as V,ah as de,D as u,x as ge,aO as ce,ag as fe,o as l,c as t,a as w,J as s,I as g,bg as S,K as p,F as m,d as C,t as $,i as d,bh as ve,k as G,U as Y,l as Z,V as P,W as B,h as O,r as q,L as W,bi as pe,bj as be,b as Q,H as X}from"./79GkDzXa.js";import{g as me}from"./6QEa5FEc.js";const ye={wrapper:"w-full relative overflow-hidden",inner:"w-0 flex-1",title:"text-sm font-medium",description:"mt-1 text-sm leading-4 opacity-90",actions:"flex items-center gap-2 mt-3 flex-shrink-0",shadow:"",rounded:"rounded-lg",padding:"p-4",gap:"gap-3",icon:{base:"flex-shrink-0 w-5 h-5"},avatar:{base:"flex-shrink-0 self-center",size:"md"},color:{white:{solid:"text-gray-900 dark:text-white bg-white dark:bg-gray-900 ring-1 ring-gray-200 dark:ring-gray-800"}},variant:{solid:"bg-{color}-500 dark:bg-{color}-400 text-white dark:text-gray-900",outline:"text-{color}-500 dark:text-{color}-400 ring-1 ring-inset ring-{color}-500 dark:ring-{color}-400",soft:"bg-{color}-50 dark:bg-{color}-400 dark:bg-opacity-10 text-{color}-500 dark:text-{color}-400",subtle:"bg-{color}-50 dark:bg-{color}-400 dark:bg-opacity-10 text-{color}-500 dark:text-{color}-400 ring-1 ring-inset ring-{color}-500 dark:ring-{color}-400 ring-opacity-25 dark:ring-opacity-25"},default:{color:"white",variant:"solid",icon:null,closeButton:null,actionButton:{size:"xs",color:"primary",variant:"link"}}},he={wrapper:"",inner:"",label:{wrapper:"flex content-center items-center justify-between",base:"block font-medium text-gray-700 dark:text-gray-200",required:"after:content-['*'] after:ms-0.5 after:text-red-500 dark:after:text-red-400"},size:{"2xs":"text-xs",xs:"text-xs",sm:"text-sm",md:"text-sm",lg:"text-sm",xl:"text-base"},container:"mt-1 relative",description:"text-gray-500 dark:text-gray-400",hint:"text-gray-500 dark:text-gray-400",help:"mt-2 text-gray-500 dark:text-gray-400",error:"mt-2 text-red-500 dark:text-red-400",default:{size:"sm"}},F=L(y.ui.strategy,y.ui.formGroup,he),ke=D({inheritAttrs:!1,props:{name:{type:String,default:null},size:{type:String,default:null,validator(e){return Object.keys(F.size).includes(e)}},label:{type:String,default:null},description:{type:String,default:null},required:{type:Boolean,default:!1},help:{type:String,default:null},error:{type:[String,Boolean],default:null},hint:{type:String,default:null},class:{type:[String,Object,Array],default:()=>""},ui:{type:Object,default:()=>({})},eagerValidation:{type:Boolean,default:!1}},setup(e){const{ui:n,attrs:h}=J("formGroup",V(e,"ui"),F,V(e,"class")),a=de("form-errors",null),k=u(()=>{var i,v;return e.error&&typeof e.error=="string"||typeof e.error=="boolean"?e.error:(v=(i=a==null?void 0:a.value)==null?void 0:i.find(r=>r.path===e.name))==null?void 0:v.message}),c=u(()=>n.value.size[e.size??F.default.size]),f=ge(ce());return fe("form-group",{error:k,inputId:f,name:u(()=>e.name),size:u(()=>e.size),eagerValidation:u(()=>e.eagerValidation)}),{ui:n,attrs:h,inputId:f,size:c,error:k}}}),$e=["for"];function Ae(e,n,h,a,k,c){return l(),t("div",p({class:e.ui.wrapper},e.attrs),[w("div",{class:s(e.ui.inner)},[e.label||e.$slots.label?(l(),t("div",{key:0,class:s([e.ui.label.wrapper,e.size])},[w("label",{for:e.inputId,class:s([e.ui.label.base,e.required?e.ui.label.required:""])},[e.$slots.label?g(e.$slots,"label",S(p({key:0},{error:e.error,label:e.label,name:e.name,hint:e.hint,description:e.description,help:e.help}))):(l(),t(m,{key:1},[C($(e.label),1)],64))],10,$e),e.hint||e.$slots.hint?(l(),t("span",{key:0,class:s([e.ui.hint])},[e.$slots.hint?g(e.$slots,"hint",S(p({key:0},{error:e.error,label:e.label,name:e.name,hint:e.hint,description:e.description,help:e.help}))):(l(),t(m,{key:1},[C($(e.hint),1)],64))],2)):d("",!0)],2)):d("",!0),e.description||e.$slots.description?(l(),t("p",{key:1,class:s([e.ui.description,e.size])},[e.$slots.description?g(e.$slots,"description",S(p({key:0},{error:e.error,label:e.label,name:e.name,hint:e.hint,description:e.description,help:e.help}))):(l(),t(m,{key:1},[C($(e.description),1)],64))],2)):d("",!0)],2),w("div",{class:s([e.label?e.ui.container:""])},[g(e.$slots,"default",S(ve({error:e.error}))),typeof e.error=="string"&&e.error?(l(),t("p",{key:0,class:s([e.ui.error,e.size])},[e.$slots.error?g(e.$slots,"error",S(p({key:0},{error:e.error,label:e.label,name:e.name,hint:e.hint,description:e.description,help:e.help}))):(l(),t(m,{key:1},[C($(e.error),1)],64))],2)):e.help||e.$slots.help?(l(),t("p",{key:1,class:s([e.ui.help,e.size])},[e.$slots.help?g(e.$slots,"help",S(p({key:0},{error:e.error,label:e.label,name:e.name,hint:e.hint,description:e.description,help:e.help}))):(l(),t(m,{key:1},[C($(e.help),1)],64))],2)):d("",!0)],2)],16)}const Ue=T(ke,[["render",Ae]]),I=L(y.ui.strategy,y.ui.alert,ye),Ie=D({components:{UIcon:G,UAvatar:Y,UButton:Z},inheritAttrs:!1,props:{title:{type:String,default:null},description:{type:String,default:null},icon:{type:String,default:()=>I.default.icon},avatar:{type:Object,default:null},closeButton:{type:Object,default:()=>I.default.closeButton},actions:{type:Array,default:()=>[]},color:{type:String,default:()=>I.default.color,validator(e){return[...y.ui.colors,...Object.keys(I.color)].includes(e)}},variant:{type:String,default:()=>I.default.variant,validator(e){return[...Object.keys(I.variant),...Object.values(I.color).flatMap(n=>Object.keys(n))].includes(e)}},class:{type:[String,Object,Array],default:()=>""},ui:{type:Object,default:()=>({})}},emits:["close"],setup(e){const{ui:n,attrs:h}=J("alert",V(e,"ui"),I),a=u(()=>{var f,i;const c=((i=(f=n.value.color)==null?void 0:f[e.color])==null?void 0:i[e.variant])||n.value.variant[e.variant];return P(B(n.value.wrapper,n.value.rounded,n.value.shadow,n.value.padding,c==null?void 0:c.replaceAll("{color}",e.color)),e.class)});function k(c){c.click&&c.click()}return{ui:n,attrs:h,alertClass:a,onAction:k,twMerge:P}}});function ze(e,n,h,a,k,c){const f=G,i=Y,v=Z;return l(),t("div",p({class:e.alertClass},e.attrs),[w("div",{class:s(["flex",[e.ui.gap,{"items-start":e.description||e.$slots.description,"items-center":!e.description&&!e.$slots.description}]])},[g(e.$slots,"icon",{icon:e.icon},()=>[e.icon?(l(),O(f,{key:0,name:e.icon,class:s(e.ui.icon.base)},null,8,["name","class"])):d("",!0)]),g(e.$slots,"avatar",{avatar:e.avatar},()=>[e.avatar?(l(),O(i,p({key:0},{size:e.ui.avatar.size,...e.avatar},{class:e.ui.avatar.base}),null,16,["class"])):d("",!0)]),w("div",{class:s(e.ui.inner)},[e.title||e.$slots.title?(l(),t("p",{key:0,class:s(e.ui.title)},[g(e.$slots,"title",{title:e.title},()=>[C($(e.title),1)])],2)):d("",!0),e.description||e.$slots.description?(l(),t("div",{key:1,class:s(e.twMerge(e.ui.description,!e.title&&!e.$slots.title&&"mt-0 leading-5"))},[g(e.$slots,"description",{description:e.description},()=>[C($(e.description),1)])],2)):d("",!0),(e.description||e.$slots.description)&&(e.actions.length||e.$slots.actions)?(l(),t("div",{key:2,class:s(e.ui.actions)},[g(e.$slots,"actions",{},()=>[(l(!0),t(m,null,q(e.actions,(r,z)=>(l(),O(v,p({key:z,ref_for:!0},{...e.ui.default.actionButton||{},...r},{onClick:W(M=>e.onAction(r),["stop"])}),null,16,["onClick"]))),128))])],2)):d("",!0)],2),e.closeButton||!e.description&&!e.$slots.description&&e.actions.length?(l(),t("div",{key:0,class:s(e.twMerge(e.ui.actions,"mt-0"))},[!e.description&&!e.$slots.description&&(e.actions.length||e.$slots.actions)?g(e.$slots,"actions",{key:0},()=>[(l(!0),t(m,null,q(e.actions,(r,z)=>(l(),O(v,p({key:z,ref_for:!0},{...e.ui.default.actionButton||{},...r},{onClick:W(M=>e.onAction(r),["stop"])}),null,16,["onClick"]))),128))]):d("",!0),e.closeButton?(l(),O(v,p({key:1,"aria-label":"Close"},{...e.ui.default.closeButton||{},...e.closeButton},{onClick:n[0]||(n[0]=W(r=>e.$emit("close"),["stop"]))}),null,16)):d("",!0)],2)):d("",!0)],2)],16)}const qe=T(Ie,[["render",ze]]),b=L(y.ui.strategy,y.ui.select,pe),Ce=D({components:{UIcon:G},inheritAttrs:!1,props:{modelValue:{type:[String,Number,Object],default:""},id:{type:String,default:null},name:{type:String,default:null},placeholder:{type:String,default:null},required:{type:Boolean,default:!1},disabled:{type:Boolean,default:!1},icon:{type:String,default:null},loadingIcon:{type:String,default:()=>b.default.loadingIcon},leadingIcon:{type:String,default:null},trailingIcon:{type:String,default:()=>b.default.trailingIcon},trailing:{type:Boolean,default:!1},leading:{type:Boolean,default:!1},loading:{type:Boolean,default:!1},padded:{type:Boolean,default:!0},options:{type:Array,default:()=>[]},size:{type:String,default:null,validator(e){return Object.keys(b.size).includes(e)}},color:{type:String,default:()=>b.default.color,validator(e){return[...y.ui.colors,...Object.keys(b.color)].includes(e)}},variant:{type:String,default:()=>b.default.variant,validator(e){return[...Object.keys(b.variant),...Object.values(b.color).flatMap(n=>Object.keys(n))].includes(e)}},optionAttribute:{type:String,default:"label"},valueAttribute:{type:String,default:"value"},selectClass:{type:String,default:null},class:{type:[String,Object,Array],default:()=>""},ui:{type:Object,default:()=>({})}},emits:["update:modelValue","change"],setup(e,{emit:n,slots:h}){const{ui:a,attrs:k}=J("select",V(e,"ui"),b,V(e,"class")),{size:c,rounded:f}=be({ui:a,props:e}),{emitFormChange:i,inputId:v,color:r,size:z,name:M}=me(e,b),A=u(()=>c.value??z.value),_=o=>{n("update:modelValue",o.target.value)},x=o=>{n("change",o.target.value),i()},ee=o=>X(o,e.valueAttribute,""),ae=o=>X(o,e.optionAttribute,""),R=o=>["string","number","boolean"].includes(typeof o)?{[e.valueAttribute]:o,[e.optionAttribute]:o}:{...o,[e.valueAttribute]:ee(o),[e.optionAttribute]:ae(o)},H=u(()=>e.options.map(o=>R(o))),K=u(()=>e.placeholder?[{[e.valueAttribute]:"",[e.optionAttribute]:e.placeholder,disabled:!0},...H.value]:H.value),le=u(()=>{const o=R(e.modelValue),j=K.value.find(U=>U[e.valueAttribute]===o[e.valueAttribute]);return j?j[e.valueAttribute]:""}),te=u(()=>{var j,U;const o=((U=(j=a.value.color)==null?void 0:j[r.value])==null?void 0:U[e.variant])||a.value.variant[e.variant];return P(B(a.value.base,a.value.form,f.value,a.value.size[A.value],e.padded?a.value.padding[A.value]:"p-0",o==null?void 0:o.replaceAll("{color}",r.value),(N.value||h.leading)&&a.value.leading.padding[A.value],(E.value||h.trailing)&&a.value.trailing.padding[A.value]),e.placeholder&&!e.modelValue&&a.value.placeholder,e.selectClass)}),N=u(()=>e.icon&&e.leading||e.icon&&!e.trailing||e.loading&&!e.trailing||e.leadingIcon),E=u(()=>e.icon&&e.trailing||e.loading&&e.trailing||e.trailingIcon),ne=u(()=>e.loading?e.loadingIcon:e.leadingIcon||e.icon),ie=u(()=>e.loading&&!N.value?e.loadingIcon:e.trailingIcon||e.icon),re=u(()=>B(a.value.icon.leading.wrapper,a.value.icon.leading.pointer,a.value.icon.leading.padding[A.value])),oe=u(()=>B(a.value.icon.base,r.value&&y.ui.colors.includes(r.value)&&a.value.icon.color.replaceAll("{color}",r.value),a.value.icon.size[A.value],e.loading&&a.value.icon.loading)),se=u(()=>B(a.value.icon.trailing.wrapper,a.value.icon.trailing.pointer,a.value.icon.trailing.padding[A.value])),ue=u(()=>B(a.value.icon.base,r.value&&y.ui.colors.includes(r.value)&&a.value.icon.color.replaceAll("{color}",r.value),a.value.icon.size[A.value],e.loading&&!N.value&&a.value.icon.loading));return{ui:a,attrs:k,name:M,inputId:v,normalizedOptionsWithPlaceholder:K,normalizedValue:le,isLeading:N,isTrailing:E,selectClass:te,leadingIconName:ne,leadingIconClass:oe,leadingWrapperIconClass:re,trailingIconName:ie,trailingIconClass:ue,trailingWrapperIconClass:se,onInput:_,onChange:x}}}),Se=["id","name","value","required","disabled"],Be=["value","label"],we=["value","selected","disabled","textContent"],je=["value","selected","disabled","textContent"];function Oe(e,n,h,a,k,c){const f=G;return l(),t("div",{class:s(e.ui.wrapper)},[w("select",p({id:e.inputId,name:e.name,value:e.modelValue,required:e.required,disabled:e.disabled,class:e.selectClass},e.attrs,{onInput:n[0]||(n[0]=(...i)=>e.onInput&&e.onInput(...i)),onChange:n[1]||(n[1]=(...i)=>e.onChange&&e.onChange(...i))}),[(l(!0),t(m,null,q(e.normalizedOptionsWithPlaceholder,(i,v)=>(l(),t(m,null,[i.children?(l(),t("optgroup",{key:`${i[e.valueAttribute]}-optgroup-${v}`,value:i[e.valueAttribute],label:i[e.optionAttribute]},[(l(!0),t(m,null,q(i.children,(r,z)=>(l(),t("option",{key:`${r[e.valueAttribute]}-${v}-${z}`,value:r[e.valueAttribute],selected:r[e.valueAttribute]===e.normalizedValue,disabled:r.disabled,textContent:$(r[e.optionAttribute])},null,8,we))),128))],8,Be)):(l(),t("option",{key:`${i[e.valueAttribute]}-${v}`,value:i[e.valueAttribute],selected:i[e.valueAttribute]===e.normalizedValue,disabled:i.disabled,textContent:$(i[e.optionAttribute])},null,8,je))],64))),256))],16,Se),e.isLeading&&e.leadingIconName||e.$slots.leading?(l(),t("span",{key:0,class:s(e.leadingWrapperIconClass)},[g(e.$slots,"leading",{disabled:e.disabled,loading:e.loading},()=>[Q(f,{name:e.leadingIconName,class:s(e.leadingIconClass)},null,8,["name","class"])],!0)],2)):d("",!0),e.isTrailing&&e.trailingIconName||e.$slots.trailing?(l(),t("span",{key:1,class:s(e.trailingWrapperIconClass)},[g(e.$slots,"trailing",{disabled:e.disabled,loading:e.loading},()=>[Q(f,{name:e.trailingIconName,class:s(e.trailingIconClass),"aria-hidden":"true"},null,8,["name","class"])],!0)],2)):d("",!0)],2)}const Ge=T(Ce,[["render",Oe],["__scopeId","data-v-9f80dc9e"]]);export{Ue as _,qe as a,Ge as b};
