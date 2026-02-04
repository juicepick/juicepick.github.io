// 검색 기능 분리 (로딩 안정성 확보 및 전역 변수 접근 수정)
console.log("🚀 Search module loaded.");

window.initSearch = function () {
    const btn = document.querySelector(".search-btn");
    const input = document.getElementById("mainSearch");

    console.log("🔍 Initializing search...", { btn, input });

    if (btn) {
        btn.onclick = function (e) {
            e.preventDefault();
            console.log("🖱️ Search button clicked");
            window.applyFilters();
        };
    }

    if (input) {
        input.onkeyup = function (e) {
            if (e.key === 'Enter') {
                console.log("⌨️ Enter key pressed");
                window.applyFilters();
            }
        };
    }
};

window.applyFilters = function () {
    console.log("🔎 applyFilters called");

    // 데이터 로딩 체크 (window.allCards 사용)
    if (!window.allCards || window.allCards.length === 0) {
        // 혹시 모르니 다시 한번 가져와 본다
        const grid = document.getElementById('productGrid');
        if (grid && grid.children.length > 0) {
            window.allCards = Array.from(grid.children);
            window.filteredCards = [...window.allCards];
            console.log("♻️ allCards recovered from DOM");
        } else {
            alert('데이터 시스템 로딩 중입니다. 1~2초 후 다시 시도해주세요.');
            return;
        }
    }

    try {
        const input = document.getElementById('mainSearch');
        if (!input) return;

        const rawQuery = input.value;
        const query = rawQuery.toLowerCase().replace(/\s+/g, '');

        const spinner = document.getElementById('loading-spinner');
        if (spinner) spinner.style.display = 'flex';

        setTimeout(() => {
            // window.allCards 및 window.currentCategory 사용
            window.filteredCards = window.allCards.filter(card => {
                const currentCat = (typeof window.currentCategory !== 'undefined') ? window.currentCategory : 'all';
                const catMatch = (currentCat === 'all') || (card.dataset.category === currentCat);

                const titleEl = card.querySelector('.product-title');
                if (!titleEl) return false;

                const title = titleEl.innerText.toLowerCase().split(' ').join('');
                const searchMatch = title.includes(query);

                return catMatch && searchMatch;
            });

            // window.sortData 호출 (전역 함수)
            if (typeof window.sortData === 'function') {
                window.sortData(false);
            } else {
                console.error("❌ sortData function not found!");
            }

            if (spinner) spinner.style.display = 'none';

            // 결과 알림
            if (query.length > 0) {
                alert(`검색 완료: ${window.filteredCards.length}개의 상품을 찾았습니다.`);
            }

        }, 50);

    } catch (e) {
        console.error("Search error:", e);
        alert("검색 중 오류: " + e.message);
    }
};

// DOMContentLoaded 시점에 초기화
document.addEventListener("DOMContentLoaded", function () {
    window.initSearch();
});

// dataReady 이벤트 수신 (build_site.py에서 발송)
window.addEventListener('dataReady', function () {
    console.log("✅ Data Ready Event Received! Products:", window.allCards ? window.allCards.length : 0);
});
