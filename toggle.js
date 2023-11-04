function toggleState(obj) {
    if (obj.className == 'bingo_sq inactive') {
	    obj.className = 'bingo_sq active';
    } else if (obj.className == 'bingo_sq active') {
	    obj.className = 'bingo_sq blocked';
    } else if (obj.className == 'bingo_sq blocked') {
	    obj.className = 'bingo_sq inactive';
    } else {
	    prop.className = 'bingo_sq inactive';
    }

    console.log("Updating state for " + obj);

    updateState();
}

function incCounterDeaths(inc) {
    cnt = document.getElementById("death_counter");
    var val = parseInt(cnt.textContent);
    val = inc ? val + 1 : val - 1;
    val = Math.max(val, 0);
    cnt.textContent = val.toString();

    updateState();
}

function incCounterMIAB(inc) {
    cnt = document.getElementById("miab_counter");
    var val = parseInt(cnt.textContent);
    val = inc ? val + 1 : val - 1;
    val = Math.max(val, 0);
    cnt.textContent = val.toString();

    updateState();
}

function loadStateFromQParams() {
    let params = new URLSearchParams(window.location.search);

    deaths = document.getElementById("death_counter");
    deaths.textContent = params.get('deaths') || '0';
    miab = document.getElementById("miab_counter");
    miab.textContent = params.get('miab') || '0';

    console.log(params);
    setState(params.get('state'));
}

function updateState() {
    let url = window.location.href.split("?")[0];
    // TODO: get death and MIAB counters
    console.log("Updating state");

    // States of counters
    deaths = document.getElementById("death_counter").innerText;
    url += "?deaths=" + deaths.trim();
    miab = document.getElementById("miab_counter").innerText;
    url += "&miab=" + miab.trim();

    url += "&state=" + getState();

    //window.location.replace(url);
    window.history.replaceState({}, "", url)
}

window.addEventListener("load", (event) => {
    console.log("Checking for state.");
    loadStateFromQParams();
})

function getState() {
    let possible_states = [
        "inactive",
        "active",
        "blocked"
    ];
    let state_list = [...document.querySelectorAll('.bingo_sq')].map((node) => {
        return String.fromCharCode(possible_states.indexOf(node.className.split(" ")[1]));
    });

    return btoa(state_list.join(""));
}

function setState(state) {
    if (state === null) {
        return;
    }

    let possible_states = [
        "inactive",
        "active",
        "blocked"
    ];

    state = atob(state)
    console.log("Setting state from " + state)
    document.querySelectorAll('.bingo_sq').forEach((node, i) => {
        node.className = "bingo_sq " + possible_states[state[i].charCodeAt(0)];
    });
}