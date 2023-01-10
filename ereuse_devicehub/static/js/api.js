const Api = {
    /**
     * get lots id
     * @returns get lots
     */
    async get_lots() {
        const request = await this.doRequest(`${API_URLS.lots}`, "GET", null);
        if (request != undefined) return request.items;
        throw request;
    },

    /**
     * Get filtered devices info
     * @param {number[]} ids devices ids
     * @returns full detailed device list
     */
    async get_devices(ids) {
        const request = await this.doRequest(`${API_URLS.devices  }?filter={"id": [${  ids.toString()  }]}`, "GET", null);
        if (request != undefined) return request.items;
        throw request;
    },

    /**
         * Get filtered devices info
         * @param {number[]} ids devices ids
         * @returns full detailed device list
         */
    async search_device(id) {
        const request = await this.doRequest(`${API_URLS.devices  }?filter={"devicehub_id": ["${  id  }"]}`, "GET", null)
        if (request != undefined) return request.items
        throw request
    },

    /**
     * Add devices to lot
     * @param {number} lotID lot id
     * @param {number[]} listDevices list devices id
     */
    async devices_add(lotID, listDevices) {
        const queryURL = `${API_URLS.devices_modify.replace("UUID", lotID)  }?${  listDevices.map(deviceID => `id=${  deviceID}`).join("&")}`;
        return Api.doRequest(queryURL, "POST", null);
    },

    /**
     * Remove devices from a lot
     * @param {number} lotID lot id
     * @param {number[]} listDevices list devices id
     */
    async devices_remove(lotID, listDevices) {
        const queryURL = `${API_URLS.devices_modify.replace("UUID", lotID)  }?${  listDevices.map(deviceID => `id=${  deviceID}`).join("&")}`;
        return Api.doRequest(queryURL, "DELETE", null);
    },

    /**
     * 
     * @param {string} url URL to be requested
     * @param {String} type Action type
     * @param {String | Object} body body content
     * @returns 
     */
    async doRequest(url, type, body) {
        let result;
        try {
            result = await $.ajax({
                url,
                type,
                headers: { "Authorization": API_URLS.Auth_Token },
                body
            });
            return result;
        } catch (error) {
            console.error(error);
            throw error;
        }
    }
}