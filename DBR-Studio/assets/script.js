
async function loadPosts(targetSelector, filterTag=null){
  try{
    const res = await fetch('./posts/posts.json?_=' + Date.now());
    const posts = await res.json();
    const target = document.querySelector(targetSelector);
    if(!target) return;
    const items = posts
      .filter(p => !filterTag || (p.tags||[]).includes(filterTag))
      .sort((a,b)=> new Date(b.date) - new Date(a.date));
    if(items.length === 0){
      target.innerHTML = '<p class="small">No posts yet. Be the first to contribute!</p>';
      return;
    }
    target.innerHTML = items.map(p => `
      <article class="post">
        <div class="kicker">${new Date(p.date).toLocaleDateString()}</div>
        <h4>${p.title}</h4>
        <p>${p.summary||''}</p>
        <div>${(p.tags||[]).map(t=>`<span class="tag">${t}</span>`).join('')}</div>
        ${p.embed ? `<div style="margin-top:10px">${p.embed}</div>` : ''}
        ${p.image ? `<figure style="margin-top:10px">
            <img src="${p.image}" alt="${p.title}" style="width:100%;border-radius:12px;"/>
            ${p.caption?`<figcaption>${p.caption}</figcaption>`:''}
          </figure>` : ''}
        ${p.link ? `<p><a href="${p.link}" target="_blank" rel="noopener">Open link</a></p>` : ''}
      </article>
    `).join('');
  }catch(e){
    console.error(e);
  }
}

function initLocalPoll(pollId){
  const key = 'poll:'+pollId;
  const form = document.getElementById(pollId);
  if(!form) return;
  const saved = localStorage.getItem(key);
  if(saved){
    form.querySelectorAll('input,button').forEach(el=>el.disabled=true);
    const result = JSON.parse(saved);
    form.querySelector('.poll-result').textContent = 'You voted: ' + result.choice;
    form.classList.add('voted');
  }
  form.addEventListener('submit', (e)=>{
    e.preventDefault();
    const data = new FormData(form);
    const choice = data.get('choice');
    if(!choice) return;
    localStorage.setItem(key, JSON.stringify({choice, at: Date.now()}));
    form.querySelectorAll('input,button').forEach(el=>el.disabled=true);
    form.querySelector('.poll-result').textContent = 'Thanks! You voted: ' + choice + ' (local only)';
  });
}

document.addEventListener('DOMContentLoaded', ()=>{
  const lp = document.querySelector('[data-load="latest"]');
  if(lp) loadPosts('[data-load="latest"]');
});
