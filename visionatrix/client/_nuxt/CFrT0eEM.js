import{K as z,s as u,ax as w,bv as G,_,o as F,c as L,a as x,y as P,x as O,n as b,b as A,h as M,l as $,f as ee,A as ae,B as q,C as ne,bw as le,D as C,bk as te,W as ie,S as ue,G as oe,E as I,a3 as de}from"./CgZMe2Un.js";function Ie(e,l,t){let a=z(t==null?void 0:t.value),n=u(()=>e.value!==void 0);return[u(()=>n.value?e.value:a.value),function(o){return n.value||(a.value=o),l==null?void 0:l(o)}]}function re(e){typeof queueMicrotask=="function"?queueMicrotask(e):Promise.resolve().then(e).catch(l=>setTimeout(()=>{throw l}))}function se(){let e=[],l={addEventListener(t,a,n,o){return t.addEventListener(a,n,o),l.add(()=>t.removeEventListener(a,n,o))},requestAnimationFrame(...t){let a=requestAnimationFrame(...t);l.add(()=>cancelAnimationFrame(a))},nextFrame(...t){l.requestAnimationFrame(()=>{l.requestAnimationFrame(...t)})},setTimeout(...t){let a=setTimeout(...t);l.add(()=>clearTimeout(a))},microTask(...t){let a={current:!0};return re(()=>{a.current&&t[0]()}),l.add(()=>{a.current=!1})},style(t,a,n){let o=t.style.getPropertyValue(a);return Object.assign(t.style,{[a]:n}),this.add(()=>{Object.assign(t.style,{[a]:o})})},group(t){let a=se();return t(a),this.add(()=>a.dispose())},add(t){return e.push(t),()=>{let a=e.indexOf(t);if(a>=0)for(let n of e.splice(a,1))n()}},dispose(){for(let t of e.splice(0))t()}};return l}function ce(e){function l(){document.readyState!=="loading"&&(e(),document.removeEventListener("DOMContentLoaded",l))}typeof window<"u"&&typeof document<"u"&&(document.addEventListener("DOMContentLoaded",l),l())}let h=[];ce(()=>{function e(l){l.target instanceof HTMLElement&&l.target!==document.body&&h[0]!==l.target&&(h.unshift(l.target),h=h.filter(t=>t!=null&&t.isConnected),h.splice(10))}window.addEventListener("click",e,{capture:!0}),window.addEventListener("mousedown",e,{capture:!0}),window.addEventListener("focus",e,{capture:!0}),document.body.addEventListener("click",e,{capture:!0}),document.body.addEventListener("mousedown",e,{capture:!0}),document.body.addEventListener("focus",e,{capture:!0})});function fe(e={},l=null,t=[]){for(let[a,n]of Object.entries(e))D(t,V(l,a),n);return t}function V(e,l){return e?e+"["+l+"]":l}function D(e,l,t){if(Array.isArray(t))for(let[a,n]of t.entries())D(e,V(l,a.toString()),n);else t instanceof Date?e.push([l,t.toISOString()]):typeof t=="boolean"?e.push([l,t?"1":"0"]):typeof t=="string"?e.push([l,t]):typeof t=="number"?e.push([l,`${t}`]):t==null?e.push([l,""]):fe(t,l,e)}function he(e){var l,t;let a=(l=e==null?void 0:e.form)!=null?l:e.closest("form");if(a){for(let n of a.elements)if(n!==e&&(n.tagName==="INPUT"&&n.type==="submit"||n.tagName==="BUTTON"&&n.type==="submit"||n.nodeName==="INPUT"&&n.type==="image")){n.click();return}(t=a.requestSubmit)==null||t.call(a)}}const ge=(e,l,t=!0)=>{const a=w("form-events",void 0),n=w("form-group",void 0),o=w("form-inputs",void 0);n&&(!t||e!=null&&e.legend?n.inputId.value=void 0:e!=null&&e.id&&(n.inputId.value=e==null?void 0:e.id),o&&(o.value[n.name.value]=n.inputId.value));const v=z(!1);function d(c,m){a&&a.emit({type:c,path:m})}function B(){d("blur",n==null?void 0:n.name.value),v.value=!0}function N(){d("change",n==null?void 0:n.name.value)}const r=G(()=>{(v.value||n!=null&&n.eagerValidation.value)&&d("input",n==null?void 0:n.name.value)},300);return{inputId:u(()=>(e==null?void 0:e.id)??(n==null?void 0:n.inputId.value)),name:u(()=>(e==null?void 0:e.name)??(n==null?void 0:n.name.value)),size:u(()=>{var m;const c=l.size[n==null?void 0:n.size.value]?n==null?void 0:n.size.value:null;return(e==null?void 0:e.size)??c??((m=l.default)==null?void 0:m.size)}),color:u(()=>{var c;return(c=n==null?void 0:n.error)!=null&&c.value?"red":e==null?void 0:e.color}),emitFormBlur:B,emitFormInput:r,emitFormChange:N}},s=ne(C.ui.strategy,C.ui.input,le),ve=ee({components:{UIcon:M},inheritAttrs:!1,props:{modelValue:{type:[String,Number],default:""},type:{type:String,default:"text"},id:{type:String,default:null},name:{type:String,default:null},placeholder:{type:String,default:null},required:{type:Boolean,default:!1},disabled:{type:Boolean,default:!1},autofocus:{type:Boolean,default:!1},autofocusDelay:{type:Number,default:100},icon:{type:String,default:null},loadingIcon:{type:String,default:()=>s.default.loadingIcon},leadingIcon:{type:String,default:null},trailingIcon:{type:String,default:null},trailing:{type:Boolean,default:!1},leading:{type:Boolean,default:!1},loading:{type:Boolean,default:!1},padded:{type:Boolean,default:!0},size:{type:String,default:null,validator(e){return Object.keys(s.size).includes(e)}},color:{type:String,default:()=>s.default.color,validator(e){return[...C.ui.colors,...Object.keys(s.color)].includes(e)}},variant:{type:String,default:()=>s.default.variant,validator(e){return[...Object.keys(s.variant),...Object.values(s.color).flatMap(l=>Object.keys(l))].includes(e)}},inputClass:{type:String,default:null},class:{type:[String,Object,Array],default:()=>""},ui:{type:Object,default:()=>({})},modelModifiers:{type:Object,default:()=>({})}},emits:["update:modelValue","blur","change"],setup(e,{emit:l,slots:t}){const{ui:a,attrs:n}=ae("input",q(e,"ui"),s,q(e,"class")),{size:o,rounded:v}=te({ui:a,props:e}),{emitFormBlur:d,emitFormInput:B,size:N,color:r,inputId:c,name:m}=ge(e,s),f=u(()=>o.value??N.value),y=z(ie({},e.modelModifiers,{trim:!1,lazy:!1,number:!1,nullify:!1})),k=z(null),U=()=>{var i;e.autofocus&&((i=k.value)==null||i.focus())},E=i=>{y.value.trim&&(i=i.trim()),(y.value.number||e.type==="number")&&(i=de(i)),y.value.nullify&&(i||(i=null)),l("update:modelValue",i),B()},W=i=>{y.value.lazy||E(i.target.value)},H=i=>{if(e.type==="file"){const g=i.target.files;l("change",g)}else{const g=i.target.value;l("change",g),y.value.lazy&&E(g),y.value.trim&&(i.target.value=g.trim())}},J=i=>{d(),l("blur",i)};ue(()=>{setTimeout(()=>{U()},e.autofocusDelay)});const K=u(()=>{var g,j;const i=((j=(g=a.value.color)==null?void 0:g[r.value])==null?void 0:j[e.variant])||a.value.variant[e.variant];return oe(I(a.value.base,a.value.form,v.value,a.value.placeholder,e.type==="file"&&a.value.file.base,a.value.size[f.value],e.padded?a.value.padding[f.value]:"p-0",i==null?void 0:i.replaceAll("{color}",r.value),(S.value||t.leading)&&a.value.leading.padding[f.value],(T.value||t.trailing)&&a.value.trailing.padding[f.value]),e.inputClass)}),S=u(()=>e.icon&&e.leading||e.icon&&!e.trailing||e.loading&&!e.trailing||e.leadingIcon),T=u(()=>e.icon&&e.trailing||e.loading&&e.trailing||e.trailingIcon),R=u(()=>e.loading?e.loadingIcon:e.leadingIcon||e.icon),Q=u(()=>e.loading&&!S.value?e.loadingIcon:e.trailingIcon||e.icon),X=u(()=>I(a.value.icon.leading.wrapper,a.value.icon.leading.pointer,a.value.icon.leading.padding[f.value])),Y=u(()=>I(a.value.icon.base,r.value&&C.ui.colors.includes(r.value)&&a.value.icon.color.replaceAll("{color}",r.value),a.value.icon.size[f.value],e.loading&&a.value.icon.loading)),Z=u(()=>I(a.value.icon.trailing.wrapper,a.value.icon.trailing.pointer,a.value.icon.trailing.padding[f.value])),p=u(()=>I(a.value.icon.base,r.value&&C.ui.colors.includes(r.value)&&a.value.icon.color.replaceAll("{color}",r.value),a.value.icon.size[f.value],e.loading&&!S.value&&a.value.icon.loading));return{ui:a,attrs:n,name:m,inputId:c,input:k,isLeading:S,isTrailing:T,inputClass:K,leadingIconName:R,leadingIconClass:Y,leadingWrapperIconClass:X,trailingIconName:Q,trailingIconClass:p,trailingWrapperIconClass:Z,onInput:W,onChange:H,onBlur:J}}}),me=["id","name","type","required","placeholder","disabled"];function ye(e,l,t,a,n,o){const v=M;return F(),L("div",{class:b(e.type==="hidden"?"hidden":e.ui.wrapper)},[x("input",P({id:e.inputId,ref:"input",name:e.name,type:e.type,required:e.required,placeholder:e.placeholder,disabled:e.disabled,class:e.inputClass},e.type==="file"?e.attrs:{...e.attrs,value:e.modelValue},{onInput:l[0]||(l[0]=(...d)=>e.onInput&&e.onInput(...d)),onBlur:l[1]||(l[1]=(...d)=>e.onBlur&&e.onBlur(...d)),onChange:l[2]||(l[2]=(...d)=>e.onChange&&e.onChange(...d))}),null,16,me),O(e.$slots,"default"),e.isLeading&&e.leadingIconName||e.$slots.leading?(F(),L("span",{key:0,class:b(e.leadingWrapperIconClass)},[O(e.$slots,"leading",{disabled:e.disabled,loading:e.loading},()=>[A(v,{name:e.leadingIconName,class:b(e.leadingIconClass)},null,8,["name","class"])])],2)):$("",!0),e.isTrailing&&e.trailingIconName||e.$slots.trailing?(F(),L("span",{key:1,class:b(e.trailingWrapperIconClass)},[O(e.$slots,"trailing",{disabled:e.disabled,loading:e.loading},()=>[A(v,{name:e.trailingIconName,class:b(e.trailingIconClass)},null,8,["name","class"])])],2)):$("",!0)],2)}const Ce=_(ve,[["render",ye]]);export{Ce as _,re as a,Ie as d,fe as e,se as o,he as p,h as t,ge as u};
