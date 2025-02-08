import{A as M,B as m,_ as I,f as N,c as r,o,a as w,C as u,k as a,i as c,n as s,D as d,d as h,t as B,F as C,r as A,ag as v,m as O,U as S,h as U,G as V,H as D,v as F,J as j,I as J}from"./GdS5Yh2f.js";const E={wrapper:"w-full relative overflow-hidden",inner:"w-0 flex-1",title:"text-sm font-medium",description:"mt-1 text-sm leading-4 opacity-90",actions:"flex items-center gap-2 mt-3 flex-shrink-0",shadow:"",rounded:"rounded-lg",padding:"p-4",gap:"gap-3",icon:{base:"flex-shrink-0 w-5 h-5"},avatar:{base:"flex-shrink-0 self-center",size:"md"},color:{white:{solid:"text-gray-900 dark:text-white bg-white dark:bg-gray-900 ring-1 ring-gray-200 dark:ring-gray-800"}},variant:{solid:"bg-{color}-500 dark:bg-{color}-400 text-white dark:text-gray-900",outline:"text-{color}-500 dark:text-{color}-400 ring-1 ring-inset ring-{color}-500 dark:ring-{color}-400",soft:"bg-{color}-50 dark:bg-{color}-400 dark:bg-opacity-10 text-{color}-500 dark:text-{color}-400",subtle:"bg-{color}-50 dark:bg-{color}-400 dark:bg-opacity-10 text-{color}-500 dark:text-{color}-400 ring-1 ring-inset ring-{color}-500 dark:ring-{color}-400 ring-opacity-25 dark:ring-opacity-25"},default:{color:"white",variant:"solid",icon:null,closeButton:null,actionButton:{size:"xs",color:"primary",variant:"link"}}},n=M(m.ui.strategy,m.ui.alert,E),G=N({components:{UIcon:U,UAvatar:S,UButton:O},inheritAttrs:!1,props:{title:{type:String,default:null},description:{type:String,default:null},icon:{type:String,default:()=>n.default.icon},avatar:{type:Object,default:null},closeButton:{type:Object,default:()=>n.default.closeButton},actions:{type:Array,default:()=>[]},color:{type:String,default:()=>n.default.color,validator(e){return[...m.ui.colors,...Object.keys(n.color)].includes(e)}},variant:{type:String,default:()=>n.default.variant,validator(e){return[...Object.keys(n.variant),...Object.values(n.color).flatMap(t=>Object.keys(t))].includes(e)}},class:{type:[String,Object,Array],default:()=>""},ui:{type:Object,default:()=>({})}},emits:["close"],setup(e){const{ui:t,attrs:y}=V("alert",D(e,"ui"),n),$=F(()=>{var p,g;const i=((g=(p=t.value.color)==null?void 0:p[e.color])==null?void 0:g[e.variant])||t.value.variant[e.variant];return j(J(t.value.wrapper,t.value.rounded,t.value.shadow,t.value.padding,i==null?void 0:i.replaceAll("{color}",e.color)),e.class)});function b(i){i.click&&i.click()}return{ui:t,attrs:y,alertClass:$,onAction:b,twMerge:j}}});function H(e,t,y,$,b,i){const p=U,g=S,f=O;return o(),r("div",d({class:e.alertClass},e.attrs),[w("div",{class:s(["flex",[e.ui.gap,{"items-start":e.description||e.$slots.description,"items-center":!e.description&&!e.$slots.description}]])},[u(e.$slots,"icon",{icon:e.icon},()=>[e.icon?(o(),c(p,{key:0,name:e.icon,class:s(e.ui.icon.base)},null,8,["name","class"])):a("",!0)]),u(e.$slots,"avatar",{avatar:e.avatar},()=>[e.avatar?(o(),c(g,d({key:0},{size:e.ui.avatar.size,...e.avatar},{class:e.ui.avatar.base}),null,16,["class"])):a("",!0)]),w("div",{class:s(e.ui.inner)},[e.title||e.$slots.title?(o(),r("p",{key:0,class:s(e.ui.title)},[u(e.$slots,"title",{title:e.title},()=>[h(B(e.title),1)])],2)):a("",!0),e.description||e.$slots.description?(o(),r("div",{key:1,class:s(e.twMerge(e.ui.description,!e.title&&!e.$slots.title&&"mt-0 leading-5"))},[u(e.$slots,"description",{description:e.description},()=>[h(B(e.description),1)])],2)):a("",!0),(e.description||e.$slots.description)&&(e.actions.length||e.$slots.actions)?(o(),r("div",{key:2,class:s(e.ui.actions)},[u(e.$slots,"actions",{},()=>[(o(!0),r(C,null,A(e.actions,(l,k)=>(o(),c(f,d({key:k,ref_for:!0},{...e.ui.default.actionButton||{},...l},{onClick:v(z=>e.onAction(l),["stop"])}),null,16,["onClick"]))),128))])],2)):a("",!0)],2),e.closeButton||!e.description&&!e.$slots.description&&e.actions.length?(o(),r("div",{key:0,class:s(e.twMerge(e.ui.actions,"mt-0"))},[!e.description&&!e.$slots.description&&(e.actions.length||e.$slots.actions)?u(e.$slots,"actions",{key:0},()=>[(o(!0),r(C,null,A(e.actions,(l,k)=>(o(),c(f,d({key:k,ref_for:!0},{...e.ui.default.actionButton||{},...l},{onClick:v(z=>e.onAction(l),["stop"])}),null,16,["onClick"]))),128))]):a("",!0),e.closeButton?(o(),c(f,d({key:1,"aria-label":"Close"},{...e.ui.default.closeButton||{},...e.closeButton},{onClick:t[0]||(t[0]=v(l=>e.$emit("close"),["stop"]))}),null,16)):a("",!0)],2)):a("",!0)],2)],16)}const P=I(G,[["render",H]]);export{P as _};
