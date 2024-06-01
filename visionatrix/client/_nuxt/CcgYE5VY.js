import{v as O,x as m,b7 as x,_ as N,g as P,l as H,y as M,z as w,A as B,o as n,c as p,G as v,j as z,E as b,k as y,F as K,s as W,N as J,O as R,d as j,t as G,b8 as _,C as ee,aB as te,r as ae,n as $,b as se,w as T,a as F,aG as ne,aH as oe}from"./B5Mitlnu.js";const ie={base:"inline-flex items-center justify-center text-gray-900 dark:text-white",padding:"px-1",size:{xs:"h-4 min-w-[16px] text-[10px]",sm:"h-5 min-w-[20px] text-[11px]",md:"h-6 min-w-[24px] text-[12px]"},rounded:"rounded",font:"font-medium font-sans",background:"bg-gray-100 dark:bg-gray-800",ring:"ring-1 ring-gray-300 dark:ring-gray-700 ring-inset",default:{size:"sm"}},re={base:"",background:"bg-white dark:bg-gray-900",divide:"divide-y divide-gray-200 dark:divide-gray-800",ring:"ring-1 ring-gray-200 dark:ring-gray-800",rounded:"rounded-lg",shadow:"shadow",body:{base:"",background:"",padding:"px-4 py-5 sm:p-6"},header:{base:"",background:"",padding:"px-4 py-5 sm:px-6"},footer:{base:"",background:"",padding:"px-4 py-4 sm:px-6"}},ue={wrapper:"flex items-center -space-x-px",base:"",rounded:"first:rounded-s-md last:rounded-e-md",default:{size:"sm",activeButton:{color:"primary"},inactiveButton:{color:"white"},firstButton:{color:"white",class:"rtl:[&_span:first-child]:rotate-180",icon:"i-heroicons-chevron-double-left-20-solid"},lastButton:{color:"white",class:"rtl:[&_span:last-child]:rotate-180",icon:"i-heroicons-chevron-double-right-20-solid"},prevButton:{color:"white",class:"rtl:[&_span:first-child]:rotate-180",icon:"i-heroicons-chevron-left-20-solid"},nextButton:{color:"white",class:"rtl:[&_span:last-child]:rotate-180",icon:"i-heroicons-chevron-right-20-solid"}}},k=O(m.ui.strategy,m.ui.pagination,ue),le=O(m.ui.strategy,m.ui.button,x),de=P({components:{UButton:H},inheritAttrs:!1,props:{modelValue:{type:Number,required:!0},pageCount:{type:Number,default:10},total:{type:Number,required:!0},max:{type:Number,default:7,validate(e){return e>=5&&e<Number.MAX_VALUE}},disabled:{type:Boolean,default:!1},size:{type:String,default:()=>k.default.size,validator(e){return Object.keys(le.size).includes(e)}},activeButton:{type:Object,default:()=>k.default.activeButton},inactiveButton:{type:Object,default:()=>k.default.inactiveButton},showFirst:{type:Boolean,default:!1},showLast:{type:Boolean,default:!1},firstButton:{type:Object,default:()=>k.default.firstButton},lastButton:{type:Object,default:()=>k.default.lastButton},prevButton:{type:Object,default:()=>k.default.prevButton},nextButton:{type:Object,default:()=>k.default.nextButton},divider:{type:String,default:"…"},class:{type:[String,Object,Array],default:()=>""},ui:{type:Object,default:()=>({})}},emits:["update:modelValue"],setup(e,{emit:t}){const{ui:d,attrs:l}=M("pagination",w(e,"ui"),k,w(e,"class")),o=B({get(){return e.modelValue},set(u){t("update:modelValue",u)}}),c=B(()=>Array.from({length:Math.ceil(e.total/e.pageCount)},(u,g)=>g+1)),i=B(()=>{const u=c.value.length,g=o.value,E=Math.max(e.max,5),h=Math.floor((Math.min(E,u)-5)/2),U=g-h,S=g+h,I=U-1>1,q=S+1<u,s=[];if(u<=E){for(let f=1;f<=u;f++)s.push(f);return s}if(s.push(1),I&&s.push(e.divider),!q){const f=g+h+2-u;for(let C=g-h-f;C<=g-h-1;C++)s.push(C)}for(let f=Math.max(2,U);f<=Math.min(u,S);f++)s.push(f);if(!I){const f=1-(g-h-2);for(let C=g+h+1;C<=g+h+f;C++)s.push(C)}return q&&s.push(e.divider),S<u&&s.push(u),s.length>=3&&s[1]===e.divider&&s[2]===3&&(s[1]=2),s.length>=3&&s[s.length-2]===e.divider&&s[s.length-1]===s.length&&(s[s.length-2]=s.length-1),s}),a=B(()=>o.value>1),r=B(()=>o.value<c.value.length);function L(){a.value&&(o.value=1)}function A(){r.value&&(o.value=c.value.length)}function Q(u){typeof u!="string"&&(o.value=u)}function Y(){a.value&&o.value--}function Z(){r.value&&o.value++}return{ui:d,attrs:l,currentPage:o,pages:c,displayedPages:i,canGoLastOrNext:r,canGoFirstOrPrev:a,onClickPrev:Y,onClickNext:Z,onClickPage:Q,onClickFirst:L,onClickLast:A}}});function fe(e,t,d,l,o,c){const i=H;return n(),p("div",b({class:e.ui.wrapper},e.attrs),[v(e.$slots,"first",{onClick:e.onClickFirst},()=>[e.firstButton&&e.showFirst?(n(),z(i,b({key:0,size:e.size,disabled:!e.canGoFirstOrPrev||e.disabled,class:[e.ui.base,e.ui.rounded]},{...e.ui.default.firstButton||{},...e.firstButton},{ui:{rounded:""},"aria-label":"First",onClick:e.onClickFirst}),null,16,["size","disabled","class","onClick"])):y("",!0)]),v(e.$slots,"prev",{onClick:e.onClickPrev},()=>[e.prevButton?(n(),z(i,b({key:0,size:e.size,disabled:!e.canGoFirstOrPrev||e.disabled,class:[e.ui.base,e.ui.rounded]},{...e.ui.default.prevButton||{},...e.prevButton},{ui:{rounded:""},"aria-label":"Prev",onClick:e.onClickPrev}),null,16,["size","disabled","class","onClick"])):y("",!0)]),(n(!0),p(K,null,W(e.displayedPages,(a,r)=>(n(),z(i,b({key:`${a}-${r}`,size:e.size,disabled:e.disabled,label:`${a}`,ref_for:!0},a===e.currentPage?{...e.ui.default.activeButton||{},...e.activeButton}:{...e.ui.default.inactiveButton||{},...e.inactiveButton},{class:[{"pointer-events-none":typeof a=="string","z-[1]":a===e.currentPage},e.ui.base,e.ui.rounded],ui:{rounded:""},onClick:()=>e.onClickPage(a)}),null,16,["size","disabled","label","class","onClick"]))),128)),v(e.$slots,"next",{onClick:e.onClickNext},()=>[e.nextButton?(n(),z(i,b({key:0,size:e.size,disabled:!e.canGoLastOrNext||e.disabled,class:[e.ui.base,e.ui.rounded]},{...e.ui.default.nextButton||{},...e.nextButton},{ui:{rounded:""},"aria-label":"Next",onClick:e.onClickNext}),null,16,["size","disabled","class","onClick"])):y("",!0)]),v(e.$slots,"last",{onClick:e.onClickLast},()=>[e.lastButton&&e.showLast?(n(),z(i,b({key:0,size:e.size,disabled:!e.canGoLastOrNext||e.disabled,class:[e.ui.base,e.ui.rounded]},{...e.ui.default.lastButton||{},...e.lastButton},{ui:{rounded:""},"aria-label":"Last",onClick:e.onClickLast}),null,16,["size","disabled","class","onClick"])):y("",!0)])],16)}const ke=N(de,[["render",fe]]),D=O(m.ui.strategy,m.ui.kbd,ie),pe=P({inheritAttrs:!1,props:{value:{type:String,default:null},size:{type:String,default:()=>D.default.size,validator(e){return Object.keys(D.size).includes(e)}},class:{type:[String,Object,Array],default:()=>""},ui:{type:Object,default:()=>({})}},setup(e){const{ui:t,attrs:d}=M("kbd",w(e,"ui"),D),l=B(()=>J(R(t.value.base,t.value.size[e.size],t.value.padding,t.value.rounded,t.value.font,t.value.background,t.value.ring),e.class));return{ui:t,attrs:d,kbdClass:l}}});function ce(e,t,d,l,o,c){return n(),p("kbd",b({class:e.kbdClass},e.attrs),[v(e.$slots,"default",{},()=>[j(G(e.value),1)])],16)}const X=N(pe,[["render",ce]]),V=O(m.ui.strategy,m.ui.tooltip,_),ge=P({components:{UKbd:X},inheritAttrs:!1,props:{text:{type:String,default:null},prevent:{type:Boolean,default:!1},shortcuts:{type:Array,default:()=>[]},openDelay:{type:Number,default:()=>V.default.openDelay},closeDelay:{type:Number,default:()=>V.default.closeDelay},popper:{type:Object,default:()=>({})},class:{type:[String,Object,Array],default:()=>""},ui:{type:Object,default:()=>({})}},setup(e){const{ui:t,attrs:d}=M("tooltip",w(e,"ui"),V,w(e,"class")),l=B(()=>ee({},e.popper,t.value.popper)),[o,c]=te(l.value),i=ae(!1);let a=null,r=null;function L(){r&&(clearTimeout(r),r=null),!i.value&&(a=a||setTimeout(()=>{i.value=!0,a=null},e.openDelay))}function A(){a&&(clearTimeout(a),a=null),i.value&&(r=r||setTimeout(()=>{i.value=!1,r=null},e.closeDelay))}return{ui:t,attrs:d,popper:l,trigger:o,container:c,open:i,onMouseEnter:L,onMouseLeave:A}}});function be(e,t,d,l,o,c){const i=X;return n(),p("div",b({ref:"trigger",class:e.ui.wrapper},e.attrs,{onMouseenter:t[0]||(t[0]=(...a)=>e.onMouseEnter&&e.onMouseEnter(...a)),onMouseleave:t[1]||(t[1]=(...a)=>e.onMouseLeave&&e.onMouseLeave(...a))}),[v(e.$slots,"default",{open:e.open},()=>[j(" Hover ")]),e.open&&!e.prevent?(n(),p("div",{key:0,ref:"container",class:$([e.ui.container,e.ui.width])},[se(ne,b({appear:""},e.ui.transition),{default:T(()=>{var a;return[F("div",null,[e.popper.arrow?(n(),p("div",{key:0,"data-popper-arrow":"",class:$(Object.values(e.ui.arrow))},null,2)):y("",!0),F("div",{class:$([e.ui.base,e.ui.background,e.ui.color,e.ui.rounded,e.ui.shadow,e.ui.ring])},[v(e.$slots,"text",{},()=>[j(G(e.text),1)]),(a=e.shortcuts)!=null&&a.length?(n(),p("span",{key:0,class:$(e.ui.shortcuts)},[F("span",{class:$(e.ui.middot)},"·",2),(n(!0),p(K,null,W(e.shortcuts,r=>(n(),z(i,{key:r,size:"xs"},{default:T(()=>[j(G(r),1)]),_:2},1024))),128))],2)):y("",!0)],2)])]}),_:3},16)],2)):y("",!0)],16)}const Be=N(ge,[["render",be]]),ve=O(m.ui.strategy,m.ui.card,re),ye=P({inheritAttrs:!1,props:{as:{type:String,default:"div"},class:{type:[String,Object,Array],default:()=>""},ui:{type:Object,default:()=>({})}},setup(e){const{ui:t,attrs:d}=M("card",w(e,"ui"),ve),l=B(()=>J(R(t.value.base,t.value.rounded,t.value.divide,t.value.ring,t.value.shadow,t.value.background),e.class));return{ui:t,attrs:d,cardClass:l}}});function me(e,t,d,l,o,c){return n(),z(oe(e.$attrs.onSubmit?"form":e.as),b({class:e.cardClass},e.attrs),{default:T(()=>[e.$slots.header?(n(),p("div",{key:0,class:$([e.ui.header.base,e.ui.header.padding,e.ui.header.background])},[v(e.$slots,"header")],2)):y("",!0),e.$slots.default?(n(),p("div",{key:1,class:$([e.ui.body.base,e.ui.body.padding,e.ui.body.background])},[v(e.$slots,"default")],2)):y("",!0),e.$slots.footer?(n(),p("div",{key:2,class:$([e.ui.footer.base,e.ui.footer.padding,e.ui.footer.background])},[v(e.$slots,"footer")],2)):y("",!0)]),_:3},16,["class"])}const $e=N(ye,[["render",me]]);export{Be as _,$e as a,ke as b,X as c};
