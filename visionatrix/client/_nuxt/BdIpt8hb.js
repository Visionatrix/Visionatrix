import{f as q,N as p,x as d,af as We,V as C,a2 as U,b5 as et,Z as F,a5 as X,a0 as Oe,$ as Re,F as tt,a9 as V,b6 as M,v as _,a4 as E,ag as se,ah as k,ad as at,b7 as Ie,ae as j,b8 as re,b9 as nt,ba as lt,a8 as Y,a3 as z,a1 as Fe,aR as Ye,aS as L,bb as rt,bc as ot,aT as it,ak as ut,ac as st,bd as dt,be as ft,bf as Pe,a6 as Ee,bg as ct,bh as H,aV as pt,n as K,bi as vt,ab as mt,B as gt,C as ke,_ as ht,aA as oe,i as He,o as Ne,w as Q,b as ge,E as he,k as yt,a as ye,D as bt,H as wt,I as Me,aM as Et,aN as Tt}from"./DUTaT_LT.js";import{t as qe,a as Ve,o as de}from"./m7-puyJG.js";const St={wrapper:"relative z-50",inner:"fixed inset-0 overflow-y-auto",container:"flex min-h-full items-end sm:items-center justify-center text-center",padding:"p-4 sm:p-0",margin:"sm:my-8",base:"relative text-left rtl:text-right flex flex-col",overlay:{base:"fixed inset-0 transition-opacity",background:"bg-gray-200/75 dark:bg-gray-800/75",transition:{enter:"ease-out duration-300",enterFrom:"opacity-0",enterTo:"opacity-100",leave:"ease-in duration-200",leaveFrom:"opacity-100",leaveTo:"opacity-0"}},background:"bg-white dark:bg-gray-900",ring:"",rounded:"rounded-lg",shadow:"shadow-xl",width:"w-full sm:max-w-lg",height:"",fullscreen:"w-screen h-screen",transition:{enter:"ease-out duration-300",enterFrom:"opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95",enterTo:"opacity-100 translate-y-0 sm:scale-100",leave:"ease-in duration-200",leaveFrom:"opacity-100 translate-y-0 sm:scale-100",leaveTo:"opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"}};function ze(e){if(!e)return new Set;if(typeof e=="function")return new Set(e());let t=new Set;for(let a of e.value){let l=E(a);l instanceof HTMLElement&&t.add(l)}return t}var xe=(e=>(e[e.None=1]="None",e[e.InitialFocus=2]="InitialFocus",e[e.TabLock=4]="TabLock",e[e.FocusLock=8]="FocusLock",e[e.RestoreFocus=16]="RestoreFocus",e[e.All=30]="All",e))(xe||{});let Z=Object.assign(q({name:"FocusTrap",props:{as:{type:[Object,String],default:"div"},initialFocus:{type:Object,default:null},features:{type:Number,default:30},containers:{type:[Object,Function],default:p(new Set)}},inheritAttrs:!1,setup(e,{attrs:t,slots:a,expose:l}){let n=p(null);l({el:n,$el:n});let r=d(()=>We(n)),o=p(!1);C(()=>o.value=!0),U(()=>o.value=!1),Ft({ownerDocument:r},d(()=>o.value&&!!(e.features&16)));let i=Lt({ownerDocument:r,container:n,initialFocus:d(()=>e.initialFocus)},d(()=>o.value&&!!(e.features&2)));Ct({ownerDocument:r,container:n,containers:e.containers,previousActiveElement:i},d(()=>o.value&&!!(e.features&8)));let u=et();function s(y){let g=E(n);g&&(b=>b())(()=>{j(u.value,{[re.Forwards]:()=>{se(g,k.First,{skipElements:[y.relatedTarget]})},[re.Backwards]:()=>{se(g,k.Last,{skipElements:[y.relatedTarget]})}})})}let c=p(!1);function w(y){y.key==="Tab"&&(c.value=!0,requestAnimationFrame(()=>{c.value=!1}))}function m(y){if(!o.value)return;let g=ze(e.containers);E(n)instanceof HTMLElement&&g.add(E(n));let b=y.relatedTarget;b instanceof HTMLElement&&b.dataset.headlessuiFocusGuard!=="true"&&(Qe(g,b)||(c.value?se(E(n),j(u.value,{[re.Forwards]:()=>k.Next,[re.Backwards]:()=>k.Previous})|k.WrapAround,{relativeTo:y.target}):y.target instanceof HTMLElement&&M(y.target)))}return()=>{let y={},g={ref:n,onKeydown:w,onFocusout:m},{features:b,initialFocus:h,containers:O,...T}=e;return F(tt,[!!(b&4)&&F(Oe,{as:"button",type:"button","data-headlessui-focus-guard":!0,onFocus:s,features:Re.Focusable}),X({ourProps:g,theirProps:{...t,...T},slot:y,attrs:t,slots:a,name:"FocusTrap"}),!!(b&4)&&F(Oe,{as:"button",type:"button","data-headlessui-focus-guard":!0,onFocus:s,features:Re.Focusable})])}}}),{features:xe});function $t(e){let t=p(Ve.slice());return _([e],([a],[l])=>{l===!0&&a===!1?qe(()=>{t.value.splice(0)}):l===!1&&a===!0&&(t.value=Ve.slice())},{flush:"post"}),()=>{var a;return(a=t.value.find(l=>l!=null&&l.isConnected))!=null?a:null}}function Ft({ownerDocument:e},t){let a=$t(t);C(()=>{V(()=>{var l,n;t.value||((l=e.value)==null?void 0:l.activeElement)===((n=e.value)==null?void 0:n.body)&&M(a())},{flush:"post"})}),U(()=>{t.value&&M(a())})}function Lt({ownerDocument:e,container:t,initialFocus:a},l){let n=p(null),r=p(!1);return C(()=>r.value=!0),U(()=>r.value=!1),C(()=>{_([t,a,l],(o,i)=>{if(o.every((s,c)=>(i==null?void 0:i[c])===s)||!l.value)return;let u=E(t);u&&qe(()=>{var s,c;if(!r.value)return;let w=E(a),m=(s=e.value)==null?void 0:s.activeElement;if(w){if(w===m){n.value=m;return}}else if(u.contains(m)){n.value=m;return}w?M(w):se(u,k.First|k.NoScroll)===at.Error&&console.warn("There are no focusable elements inside the <FocusTrap />"),n.value=(c=e.value)==null?void 0:c.activeElement})},{immediate:!0,flush:"post"})}),n}function Ct({ownerDocument:e,container:t,containers:a,previousActiveElement:l},n){var r;Ie((r=e.value)==null?void 0:r.defaultView,"focus",o=>{if(!n.value)return;let i=ze(a);E(t)instanceof HTMLElement&&i.add(E(t));let u=l.value;if(!u)return;let s=o.target;s&&s instanceof HTMLElement?Qe(i,s)?(l.value=s,M(s)):(o.preventDefault(),o.stopPropagation(),M(u)):M(l.value)},!0)}function Qe(e,t){for(let a of e)if(a.contains(t))return!0;return!1}function At(e){let t=nt(e.getSnapshot());return U(e.subscribe(()=>{t.value=e.getSnapshot()})),t}function Dt(e,t){let a=e(),l=new Set;return{getSnapshot(){return a},subscribe(n){return l.add(n),()=>l.delete(n)},dispatch(n,...r){let o=t[n].call(a,...r);o&&(a=o,l.forEach(i=>i()))}}}function Bt(){let e;return{before({doc:t}){var a;let l=t.documentElement;e=((a=t.defaultView)!=null?a:window).innerWidth-l.clientWidth},after({doc:t,d:a}){let l=t.documentElement,n=l.clientWidth-l.offsetWidth,r=e-n;a.style(l,"paddingRight",`${r}px`)}}}function Ot(){return lt()?{before({doc:e,d:t,meta:a}){function l(n){return a.containers.flatMap(r=>r()).some(r=>r.contains(n))}t.microTask(()=>{var n;if(window.getComputedStyle(e.documentElement).scrollBehavior!=="auto"){let i=de();i.style(e.documentElement,"scrollBehavior","auto"),t.add(()=>t.microTask(()=>i.dispose()))}let r=(n=window.scrollY)!=null?n:window.pageYOffset,o=null;t.addEventListener(e,"click",i=>{if(i.target instanceof HTMLElement)try{let u=i.target.closest("a");if(!u)return;let{hash:s}=new URL(u.href),c=e.querySelector(s);c&&!l(c)&&(o=c)}catch{}},!0),t.addEventListener(e,"touchstart",i=>{if(i.target instanceof HTMLElement)if(l(i.target)){let u=i.target;for(;u.parentElement&&l(u.parentElement);)u=u.parentElement;t.style(u,"overscrollBehavior","contain")}else t.style(i.target,"touchAction","none")}),t.addEventListener(e,"touchmove",i=>{if(i.target instanceof HTMLElement){if(i.target.tagName==="INPUT")return;if(l(i.target)){let u=i.target;for(;u.parentElement&&u.dataset.headlessuiPortal!==""&&!(u.scrollHeight>u.clientHeight||u.scrollWidth>u.clientWidth);)u=u.parentElement;u.dataset.headlessuiPortal===""&&i.preventDefault()}else i.preventDefault()}},{passive:!1}),t.add(()=>{var i;let u=(i=window.scrollY)!=null?i:window.pageYOffset;r!==u&&window.scrollTo(0,r),o&&o.isConnected&&(o.scrollIntoView({block:"nearest"}),o=null)})})}}:{}}function Rt(){return{before({doc:e,d:t}){t.style(e.documentElement,"overflow","hidden")}}}function Pt(e){let t={};for(let a of e)Object.assign(t,a(t));return t}let N=Dt(()=>new Map,{PUSH(e,t){var a;let l=(a=this.get(e))!=null?a:{doc:e,count:0,d:de(),meta:new Set};return l.count++,l.meta.add(t),this.set(e,l),this},POP(e,t){let a=this.get(e);return a&&(a.count--,a.meta.delete(t)),this},SCROLL_PREVENT({doc:e,d:t,meta:a}){let l={doc:e,d:t,meta:Pt(a)},n=[Ot(),Bt(),Rt()];n.forEach(({before:r})=>r==null?void 0:r(l)),n.forEach(({after:r})=>r==null?void 0:r(l))},SCROLL_ALLOW({d:e}){e.dispose()},TEARDOWN({doc:e}){this.delete(e)}});N.subscribe(()=>{let e=N.getSnapshot(),t=new Map;for(let[a]of e)t.set(a,a.documentElement.style.overflow);for(let a of e.values()){let l=t.get(a.doc)==="hidden",n=a.count!==0;(n&&!l||!n&&l)&&N.dispatch(a.count>0?"SCROLL_PREVENT":"SCROLL_ALLOW",a),a.count===0&&N.dispatch("TEARDOWN",a)}});function kt(e,t,a){let l=At(N),n=d(()=>{let r=e.value?l.value.get(e.value):void 0;return r?r.count>0:!1});return _([e,t],([r,o],[i],u)=>{if(!r||!o)return;N.dispatch("PUSH",r,a);let s=!1;u(()=>{s||(N.dispatch("POP",i??r,a),s=!0)})},{immediate:!0}),n}let be=new Map,G=new Map;function je(e,t=p(!0)){V(a=>{var l;if(!t.value)return;let n=E(e);if(!n)return;a(function(){var o;if(!n)return;let i=(o=G.get(n))!=null?o:1;if(i===1?G.delete(n):G.set(n,i-1),i!==1)return;let u=be.get(n);u&&(u["aria-hidden"]===null?n.removeAttribute("aria-hidden"):n.setAttribute("aria-hidden",u["aria-hidden"]),n.inert=u.inert,be.delete(n))});let r=(l=G.get(n))!=null?l:0;G.set(n,r+1),r===0&&(be.set(n,{"aria-hidden":n.getAttribute("aria-hidden"),inert:n.inert}),n.setAttribute("aria-hidden","true"),n.inert=!0)})}let Ze=Symbol("StackContext");var Te=(e=>(e[e.Add=0]="Add",e[e.Remove=1]="Remove",e))(Te||{});function Ht(){return z(Ze,()=>{})}function Nt({type:e,enabled:t,element:a,onUpdate:l}){let n=Ht();function r(...o){l==null||l(...o),n(...o)}C(()=>{_(t,(o,i)=>{o?r(0,e,a):i===!0&&r(1,e,a)},{immediate:!0,flush:"sync"})}),U(()=>{t.value&&r(1,e,a)}),Y(Ze,r)}let Mt=Symbol("DescriptionContext");function Vt({slot:e=p({}),name:t="Description",props:a={}}={}){let l=p([]);function n(r){return l.value.push(r),()=>{let o=l.value.indexOf(r);o!==-1&&l.value.splice(o,1)}}return Y(Mt,{register:n,slot:e,name:t,props:a}),d(()=>l.value.length>0?l.value.join(" "):void 0)}var jt=(e=>(e[e.Open=0]="Open",e[e.Closed=1]="Closed",e))(jt||{});let Se=Symbol("DialogContext");function Ge(e){let t=z(Se,null);if(t===null){let a=new Error(`<${e} /> is missing a parent <Dialog /> component.`);throw Error.captureStackTrace&&Error.captureStackTrace(a,Ge),a}return t}let ie="DC8F892D-2EBD-447C-A4C8-A03058436FF4",Ut=q({name:"Dialog",inheritAttrs:!1,props:{as:{type:[Object,String],default:"div"},static:{type:Boolean,default:!1},unmount:{type:Boolean,default:!0},open:{type:[Boolean,String],default:ie},initialFocus:{type:Object,default:null},id:{type:String,default:null},role:{type:String,default:"dialog"}},emits:{close:e=>!0},setup(e,{emit:t,attrs:a,slots:l,expose:n}){var r,o;let i=(r=e.id)!=null?r:`headlessui-dialog-${Fe()}`,u=p(!1);C(()=>{u.value=!0});let s=!1,c=d(()=>e.role==="dialog"||e.role==="alertdialog"?e.role:(s||(s=!0,console.warn(`Invalid role [${c}] passed to <Dialog />. Only \`dialog\` and and \`alertdialog\` are supported. Using \`dialog\` instead.`)),"dialog")),w=p(0),m=Ye(),y=d(()=>e.open===ie&&m!==null?(m.value&L.Open)===L.Open:e.open),g=p(null),b=d(()=>We(g));if(n({el:g,$el:g}),!(e.open!==ie||m!==null))throw new Error("You forgot to provide an `open` prop to the `Dialog`.");if(typeof y.value!="boolean")throw new Error(`You provided an \`open\` prop to the \`Dialog\`, but the value is not a boolean. Received: ${y.value===ie?void 0:e.open}`);let h=d(()=>u.value&&y.value?0:1),O=d(()=>h.value===0),T=d(()=>w.value>1),R=z(Se,null)!==null,[J,ee]=rt(),{resolveContainers:W,mainTreeNodeRef:te,MainTreeNode:ae}=ot({portals:J,defaultContainers:[d(()=>{var f;return(f=I.panelRef.value)!=null?f:g.value})]}),ce=d(()=>T.value?"parent":"leaf"),ne=d(()=>m!==null?(m.value&L.Closing)===L.Closing:!1),pe=d(()=>R||ne.value?!1:O.value),ve=d(()=>{var f,v,S;return(S=Array.from((v=(f=b.value)==null?void 0:f.querySelectorAll("body > *"))!=null?v:[]).find($=>$.id==="headlessui-portal-root"?!1:$.contains(E(te))&&$ instanceof HTMLElement))!=null?S:null});je(ve,pe);let A=d(()=>T.value?!0:O.value),x=d(()=>{var f,v,S;return(S=Array.from((v=(f=b.value)==null?void 0:f.querySelectorAll("[data-headlessui-portal]"))!=null?v:[]).find($=>$.contains(E(te))&&$ instanceof HTMLElement))!=null?S:null});je(x,A),Nt({type:"Dialog",enabled:d(()=>h.value===0),element:g,onUpdate:(f,v)=>{if(v==="Dialog")return j(f,{[Te.Add]:()=>w.value+=1,[Te.Remove]:()=>w.value-=1})}});let D=Vt({name:"DialogDescription",slot:d(()=>({open:y.value}))}),B=p(null),I={titleId:B,panelRef:p(null),dialogState:h,setTitleId(f){B.value!==f&&(B.value=f)},close(){t("close",!1)}};Y(Se,I);let Ae=d(()=>!(!O.value||T.value));it(W,(f,v)=>{f.preventDefault(),I.close(),ut(()=>v==null?void 0:v.focus())},Ae);let De=d(()=>!(T.value||h.value!==0));Ie((o=b.value)==null?void 0:o.defaultView,"keydown",f=>{De.value&&(f.defaultPrevented||f.key===st.Escape&&(f.preventDefault(),f.stopPropagation(),I.close()))});let Be=d(()=>!(ne.value||h.value!==0||R));return kt(b,Be,f=>{var v;return{containers:[...(v=f.containers)!=null?v:[],W]}}),V(f=>{if(h.value!==0)return;let v=E(g);if(!v)return;let S=new ResizeObserver($=>{for(let me of $){let le=me.target.getBoundingClientRect();le.x===0&&le.y===0&&le.width===0&&le.height===0&&I.close()}});S.observe(v),f(()=>S.disconnect())}),()=>{let{open:f,initialFocus:v,...S}=e,$={...a,ref:g,id:i,role:c.value,"aria-modal":h.value===0?!0:void 0,"aria-labelledby":B.value,"aria-describedby":D.value},me={open:h.value===0};return F(Pe,{force:!0},()=>[F(dt,()=>F(ft,{target:g.value},()=>F(Pe,{force:!1},()=>F(Z,{initialFocus:v,containers:W,features:O.value?j(ce.value,{parent:Z.features.RestoreFocus,leaf:Z.features.All&~Z.features.FocusLock}):Z.features.None},()=>F(ee,{},()=>X({ourProps:$,theirProps:{...S,...a},slot:me,attrs:a,slots:l,visible:h.value===0,features:Ee.RenderStrategy|Ee.Static,name:"Dialog"})))))),F(ae)])}}}),Wt=q({name:"DialogPanel",props:{as:{type:[Object,String],default:"div"},id:{type:String,default:null}},setup(e,{attrs:t,slots:a,expose:l}){var n;let r=(n=e.id)!=null?n:`headlessui-dialog-panel-${Fe()}`,o=Ge("DialogPanel");l({el:o.panelRef,$el:o.panelRef});function i(u){u.stopPropagation()}return()=>{let{...u}=e,s={id:r,ref:o.panelRef,onClick:i};return X({ourProps:s,theirProps:u,slot:{open:o.dialogState.value===0},attrs:t,slots:a,name:"DialogPanel"})}}});function It(e){let t={called:!1};return(...a)=>{if(!t.called)return t.called=!0,e(...a)}}function we(e,...t){e&&t.length>0&&e.classList.add(...t)}function ue(e,...t){e&&t.length>0&&e.classList.remove(...t)}var $e=(e=>(e.Finished="finished",e.Cancelled="cancelled",e))($e||{});function Yt(e,t){let a=de();if(!e)return a.dispose;let{transitionDuration:l,transitionDelay:n}=getComputedStyle(e),[r,o]=[l,n].map(i=>{let[u=0]=i.split(",").filter(Boolean).map(s=>s.includes("ms")?parseFloat(s):parseFloat(s)*1e3).sort((s,c)=>c-s);return u});return r!==0?a.setTimeout(()=>t("finished"),r+o):t("finished"),a.add(()=>t("cancelled")),a.dispose}function Ue(e,t,a,l,n,r){let o=de(),i=r!==void 0?It(r):()=>{};return ue(e,...n),we(e,...t,...a),o.nextFrame(()=>{ue(e,...a),we(e,...l),o.add(Yt(e,u=>(ue(e,...l,...t),we(e,...n),i(u))))}),o.add(()=>ue(e,...t,...a,...l,...n)),o.add(()=>i("cancelled")),o.dispose}function P(e=""){return e.split(/\s+/).filter(t=>t.length>1)}let Le=Symbol("TransitionContext");var qt=(e=>(e.Visible="visible",e.Hidden="hidden",e))(qt||{});function zt(){return z(Le,null)!==null}function xt(){let e=z(Le,null);if(e===null)throw new Error("A <TransitionChild /> is used but it is missing a parent <TransitionRoot />.");return e}function Qt(){let e=z(Ce,null);if(e===null)throw new Error("A <TransitionChild /> is used but it is missing a parent <TransitionRoot />.");return e}let Ce=Symbol("NestingContext");function fe(e){return"children"in e?fe(e.children):e.value.filter(({state:t})=>t==="visible").length>0}function Ke(e){let t=p([]),a=p(!1);C(()=>a.value=!0),U(()=>a.value=!1);function l(r,o=H.Hidden){let i=t.value.findIndex(({id:u})=>u===r);i!==-1&&(j(o,{[H.Unmount](){t.value.splice(i,1)},[H.Hidden](){t.value[i].state="hidden"}}),!fe(t)&&a.value&&(e==null||e()))}function n(r){let o=t.value.find(({id:i})=>i===r);return o?o.state!=="visible"&&(o.state="visible"):t.value.push({id:r,state:"visible"}),()=>l(r,H.Unmount)}return{children:t,register:n,unregister:l}}let Xe=Ee.RenderStrategy,_e=q({props:{as:{type:[Object,String],default:"div"},show:{type:[Boolean],default:null},unmount:{type:[Boolean],default:!0},appear:{type:[Boolean],default:!1},enter:{type:[String],default:""},enterFrom:{type:[String],default:""},enterTo:{type:[String],default:""},entered:{type:[String],default:""},leave:{type:[String],default:""},leaveFrom:{type:[String],default:""},leaveTo:{type:[String],default:""}},emits:{beforeEnter:()=>!0,afterEnter:()=>!0,beforeLeave:()=>!0,afterLeave:()=>!0},setup(e,{emit:t,attrs:a,slots:l,expose:n}){let r=p(0);function o(){r.value|=L.Opening,t("beforeEnter")}function i(){r.value&=~L.Opening,t("afterEnter")}function u(){r.value|=L.Closing,t("beforeLeave")}function s(){r.value&=~L.Closing,t("afterLeave")}if(!zt()&&ct())return()=>F(Je,{...e,onBeforeEnter:o,onAfterEnter:i,onBeforeLeave:u,onAfterLeave:s},l);let c=p(null),w=d(()=>e.unmount?H.Unmount:H.Hidden);n({el:c,$el:c});let{show:m,appear:y}=xt(),{register:g,unregister:b}=Qt(),h=p(m.value?"visible":"hidden"),O={value:!0},T=Fe(),R={value:!1},J=Ke(()=>{!R.value&&h.value!=="hidden"&&(h.value="hidden",b(T),s())});C(()=>{let A=g(T);U(A)}),V(()=>{if(w.value===H.Hidden&&T){if(m.value&&h.value!=="visible"){h.value="visible";return}j(h.value,{hidden:()=>b(T),visible:()=>g(T)})}});let ee=P(e.enter),W=P(e.enterFrom),te=P(e.enterTo),ae=P(e.entered),ce=P(e.leave),ne=P(e.leaveFrom),pe=P(e.leaveTo);C(()=>{V(()=>{if(h.value==="visible"){let A=E(c);if(A instanceof Comment&&A.data==="")throw new Error("Did you forget to passthrough the `ref` to the actual DOM node?")}})});function ve(A){let x=O.value&&!y.value,D=E(c);!D||!(D instanceof HTMLElement)||x||(R.value=!0,m.value&&o(),m.value||u(),A(m.value?Ue(D,ee,W,te,ae,B=>{R.value=!1,B===$e.Finished&&i()}):Ue(D,ce,ne,pe,ae,B=>{R.value=!1,B===$e.Finished&&(fe(J)||(h.value="hidden",b(T),s()))})))}return C(()=>{_([m],(A,x,D)=>{ve(D),O.value=!1},{immediate:!0})}),Y(Ce,J),pt(d(()=>j(h.value,{visible:L.Open,hidden:L.Closed})|r.value)),()=>{let{appear:A,show:x,enter:D,enterFrom:B,enterTo:I,entered:Ae,leave:De,leaveFrom:Be,leaveTo:f,...v}=e,S={ref:c},$={...v,...y.value&&m.value&&vt.isServer?{class:K([a.class,v.class,...ee,...W])}:{}};return X({theirProps:$,ourProps:S,slot:{},slots:l,attrs:a,features:Xe,visible:h.value==="visible",name:"TransitionChild"})}}}),Zt=_e,Je=q({inheritAttrs:!1,props:{as:{type:[Object,String],default:"div"},show:{type:[Boolean],default:null},unmount:{type:[Boolean],default:!0},appear:{type:[Boolean],default:!1},enter:{type:[String],default:""},enterFrom:{type:[String],default:""},enterTo:{type:[String],default:""},entered:{type:[String],default:""},leave:{type:[String],default:""},leaveFrom:{type:[String],default:""},leaveTo:{type:[String],default:""}},emits:{beforeEnter:()=>!0,afterEnter:()=>!0,beforeLeave:()=>!0,afterLeave:()=>!0},setup(e,{emit:t,attrs:a,slots:l}){let n=Ye(),r=d(()=>e.show===null&&n!==null?(n.value&L.Open)===L.Open:e.show);V(()=>{if(![!0,!1].includes(r.value))throw new Error('A <Transition /> is used but it is missing a `:show="true | false"` prop.')});let o=p(r.value?"visible":"hidden"),i=Ke(()=>{o.value="hidden"}),u=p(!0),s={show:r,appear:d(()=>e.appear||!u.value)};return C(()=>{V(()=>{u.value=!1,r.value?o.value="visible":fe(i)||(o.value="hidden")})}),Y(Ce,i),Y(Le,s),()=>{let c=mt(e,["show","appear","unmount","onBeforeEnter","onBeforeLeave","onAfterEnter","onAfterLeave"]),w={unmount:e.unmount};return X({ourProps:{...w,as:"template"},theirProps:{},slot:{},slots:{...l,default:()=>[F(Zt,{onBeforeEnter:()=>t("beforeEnter"),onAfterEnter:()=>t("afterEnter"),onBeforeLeave:()=>t("beforeLeave"),onAfterLeave:()=>t("afterLeave"),...a,...w,...c},l.default)]},attrs:{},features:Xe,visible:o.value==="visible",name:"Transition"})}}});const Gt=gt(ke.ui.strategy,ke.ui.modal,St),Kt=q({components:{HDialog:Ut,HDialogPanel:Wt,TransitionRoot:Je,TransitionChild:_e},inheritAttrs:!1,props:{modelValue:{type:Boolean,default:!1},appear:{type:Boolean,default:!1},overlay:{type:Boolean,default:!0},transition:{type:Boolean,default:!0},preventClose:{type:Boolean,default:!1},fullscreen:{type:Boolean,default:!1},class:{type:[String,Object,Array],default:()=>""},ui:{type:Object,default:()=>({})}},emits:["update:modelValue","close","close-prevented","after-leave"],setup(e,{emit:t}){const{ui:a,attrs:l}=wt("modal",Me(e,"ui"),Gt,Me(e,"class")),n=d({get(){return e.modelValue},set(u){t("update:modelValue",u)}}),r=d(()=>e.transition?{...a.value.transition}:{});function o(u){if(e.preventClose){t("close-prevented");return}n.value=u,t("close")}const i=()=>{t("after-leave")};return Et(()=>Tt()),{ui:a,attrs:l,isOpen:n,transitionClass:r,onAfterLeave:i,close:o}}});function Xt(e,t,a,l,n,r){const o=oe("TransitionChild"),i=oe("HDialogPanel"),u=oe("HDialog"),s=oe("TransitionRoot");return Ne(),He(s,{appear:e.appear,show:e.isOpen,as:"template",onAfterLeave:e.onAfterLeave},{default:Q(()=>[ge(u,he({class:e.ui.wrapper},e.attrs,{onClose:e.close}),{default:Q(()=>[e.overlay?(Ne(),He(o,he({key:0,as:"template",appear:e.appear},e.ui.overlay.transition,{class:e.ui.overlay.transition.enterFrom}),{default:Q(()=>[ye("div",{class:K([e.ui.overlay.base,e.ui.overlay.background])},null,2)]),_:1},16,["appear","class"])):yt("",!0),ye("div",{class:K(e.ui.inner)},[ye("div",{class:K([e.ui.container,!e.fullscreen&&e.ui.padding])},[ge(o,he({as:"template",appear:e.appear},e.transitionClass,{class:e.transitionClass.enterFrom}),{default:Q(()=>[ge(i,{class:K([e.ui.base,e.ui.background,e.ui.ring,e.ui.shadow,e.fullscreen?e.ui.fullscreen:[e.ui.width,e.ui.height,e.ui.rounded,e.ui.margin]])},{default:Q(()=>[bt(e.$slots,"default")]),_:3},8,["class"])]),_:3},16,["appear","class"])],2)],2)]),_:3},16,["class","onClose"])]),_:3},8,["appear","show","onAfterLeave"])}const ea=ht(Kt,[["render",Xt]]);export{ea as _};
