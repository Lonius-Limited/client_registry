import{c as f,a as d,_ as m,b as p,d as h,r as _,o as y,e as g,s as v,f as L,B as E,g as P}from"./vendor.adf9dd71.js";const b=function(){const n=document.createElement("link").relList;if(n&&n.supports&&n.supports("modulepreload"))return;for(const e of document.querySelectorAll('link[rel="modulepreload"]'))o(e);new MutationObserver(e=>{for(const t of e)if(t.type==="childList")for(const r of t.addedNodes)r.tagName==="LINK"&&r.rel==="modulepreload"&&o(r)}).observe(document,{childList:!0,subtree:!0});function s(e){const t={};return e.integrity&&(t.integrity=e.integrity),e.referrerpolicy&&(t.referrerPolicy=e.referrerpolicy),e.crossorigin==="use-credentials"?t.credentials="include":e.crossorigin==="anonymous"?t.credentials="omit":t.credentials="same-origin",t}function o(e){if(e.ep)return;e.ep=!0;const t=s(e);fetch(e.href,t)}};b();const O="modulepreload",l={},k="/assets/client_registry/frontend/",B=function(n,s){return!s||s.length===0?n():Promise.all(s.map(o=>{if(o=`${k}${o}`,o in l)return;l[o]=!0;const e=o.endsWith(".css"),t=e?'[rel="stylesheet"]':"";if(document.querySelector(`link[href="${o}"]${t}`))return;const r=document.createElement("link");if(r.rel=e?"stylesheet":O,e||(r.as="script",r.crossOrigin=""),r.href=o,document.head.appendChild(r),e)return new Promise((a,u)=>{r.addEventListener("load",a),r.addEventListener("error",u)})})).then(()=>n())},w=[{path:"/",name:"Home",component:()=>B(()=>import("./Home.71fae86b.js"),["assets/Home.71fae86b.js","assets/vendor.adf9dd71.js","assets/vendor.1f7d581e.css"])}];let A=f({history:d("/frontend"),routes:w});const C={};function N(c,n){const s=_("router-view");return y(),p("div",null,[h(s)])}var R=m(C,[["render",N]]);let i=g(R);v("resourceFetcher",P);i.use(A);i.use(L);i.component("Button",E);i.mount("#app");