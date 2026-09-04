const slides=[...document.querySelectorAll('.slide')];
const dots=document.querySelector('#dots');
const counter=document.querySelector('#counter');
let current=0;

function show(index){
  current=(index+slides.length)%slides.length;
  slides.forEach((slide,i)=>slide.classList.toggle('active',i===current));
  [...dots.children].forEach((dot,i)=>dot.classList.toggle('active',i===current));
  counter.textContent=`${current+1} / ${slides.length}`;
}

slides.forEach((_slide,index)=>{
  const dot=document.createElement('button');
  dot.type='button';
  dot.setAttribute('aria-label',`Slide ${index+1}`);
  dot.addEventListener('click',()=>show(index));
  dots.append(dot);
});

document.querySelector('#prev').addEventListener('click',()=>show(current-1));
document.querySelector('#next').addEventListener('click',()=>show(current+1));
document.addEventListener('keydown',event=>{
  if(['ArrowRight','PageDown',' '].includes(event.key))show(current+1);
  if(['ArrowLeft','PageUp'].includes(event.key))show(current-1);
});
show(0);
