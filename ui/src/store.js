// Vuex store; contains global state information for the entire UI.

import Vue from 'vue'
import Vuex from 'vuex'

Vue.use(Vuex);

export default new Vuex.Store({
    state: {
        currentLocale: 'en'
    },
    mutations: {
        setCurrentLocale(state, value) {
            state.currentLocale = value;
        }
    },
    actions: {}
});