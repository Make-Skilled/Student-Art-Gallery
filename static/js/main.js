function likeArtwork(artworkId) {
    fetch(`/like/${artworkId}`, { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                updateLikeCount(artworkId);
            } else {
                alert(data.message || 'Could not like artwork.');
            }
        });
}

function updateLikeCount(artworkId) {
    fetch(`/api/artworks/${artworkId}/likes`)
        .then(res => res.json())
        .then(data => {
            document.getElementById(`like-count-${artworkId}`).textContent = data.count;
        });
}

function toggleCommentBox(artworkId) {
    const box = document.getElementById(`comment-box-${artworkId}`);
    if (box) box.classList.toggle('hidden');
    if (!box.classList.contains('hidden')) {
        loadComments(artworkId);
    }
}

function postComment(event, artworkId) {
    event.preventDefault();
    const form = event.target;
    const content = form.content.value.trim();
    if (!content) return false;
    const formData = new FormData();
    formData.append('content', content);
    fetch(`/comment/${artworkId}`, { method: 'POST', body: formData })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                form.reset();
                updateCommentCount(artworkId);
                loadComments(artworkId);
            } else {
                alert(data.message || 'Could not post comment.');
            }
        });
    return false;
}

function updateCommentCount(artworkId) {
    fetch(`/api/artworks/${artworkId}/comments`)
        .then(res => res.json())
        .then(data => {
            document.getElementById(`comment-count-${artworkId}`).textContent = data.comments.length;
        });
}

function loadComments(artworkId) {
    fetch(`/api/artworks/${artworkId}/comments`)
        .then(res => res.json())
        .then(data => {
            const list = document.getElementById(`comments-list-${artworkId}`);
            if (list) {
                list.innerHTML = '';
                data.comments.forEach(comment => {
                    const div = document.createElement('div');
                    div.className = 'mb-1 p-1 bg-gray-100 rounded';
                    div.innerHTML = `<span class='font-semibold'>${comment.user_id.slice(0, 8)}</span>: ${comment.content} <span class='text-xs text-gray-400'>(${comment.created_at.slice(0, 10)})</span>`;
                    list.appendChild(div);
                });
            }
        });
} 