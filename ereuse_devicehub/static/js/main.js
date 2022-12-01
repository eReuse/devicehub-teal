/**
* Template Name: NiceAdmin - v2.2.0
* Template URL: https://bootstrapmade.com/nice-admin-bootstrap-admin-html-template/
* Author: BootstrapMade.com
* License: https://bootstrapmade.com/license/
*/
(function () {
  "use strict";

  /**
   * Easy selector helper function
   */
  const select = (el, all = false) => {
    el = el.trim()
    if (all) {
      return [...document.querySelectorAll(el)]
    }
    return document.querySelector(el)

  }

  /**
   * Easy event listener function
   */
  const on = (type, el, listener, all = false) => {
    if (all) {
      select(el, all).forEach(e => e.addEventListener(type, listener))
    } else {
      select(el, all).addEventListener(type, listener)
    }
  }

  /**
   * Easy on scroll event listener
   */
  const onscroll = (el, listener) => {
    el.addEventListener("scroll", listener)
  }

  /**
   * Sidebar toggle
   */
  if (select(".toggle-sidebar-btn")) {
    on("click", ".toggle-sidebar-btn", (e) => {
      select("body").classList.toggle("toggle-sidebar")
    })
  }

  /**
   * Search bar toggle
  if (select(".search-bar-toggle")) {
    on("click", ".search-bar-toggle", (e) => {
      select(".search-bar").classList.toggle("search-bar-show")
    })
  }
   */

  /**
   * Navbar links active state on scroll
   */
  const navbarlinks = select("#navbar .scrollto", true)
  const navbarlinksActive = () => {
    const position = window.scrollY + 200
    navbarlinks.forEach(navbarlink => {
      if (!navbarlink.hash) return
      const section = select(navbarlink.hash)
      if (!section) return
      if (position >= section.offsetTop && position <= (section.offsetTop + section.offsetHeight)) {
        navbarlink.classList.add("active")
      } else {
        navbarlink.classList.remove("active")
      }
    })
  }
  window.addEventListener("load", navbarlinksActive)
  onscroll(document, navbarlinksActive)

  /**
   * Toggle .header-scrolled class to #header when page is scrolled
   */
  const selectHeader = select("#header")
  if (selectHeader) {
    const headerScrolled = () => {
      if (window.scrollY > 100) {
        selectHeader.classList.add("header-scrolled")
      } else {
        selectHeader.classList.remove("header-scrolled")
      }
    }
    window.addEventListener("load", headerScrolled)
    onscroll(document, headerScrolled)
  }

  /**
   * Back to top button
   */
  const backtotop = select(".back-to-top")
  if (backtotop) {
    const toggleBacktotop = () => {
      if (window.scrollY > 100) {
        backtotop.classList.add("active")
      } else {
        backtotop.classList.remove("active")
      }
    }
    window.addEventListener("load", toggleBacktotop)
    onscroll(document, toggleBacktotop)
  }

  /**
   * Initiate tooltips
   */
  const tooltipTriggerList = [].slice.call(document.querySelectorAll("[data-bs-toggle=\"tooltip\"]"))
  const tooltipList = tooltipTriggerList.map((tooltipTriggerEl) => new bootstrap.Tooltip(tooltipTriggerEl))

  /**
   * Initiate quill editors
   */
  if (select(".quill-editor-default")) {
    new Quill(".quill-editor-default", {
      theme: "snow"
    });
  }

  if (select(".quill-editor-bubble")) {
    new Quill(".quill-editor-bubble", {
      theme: "bubble"
    });
  }

  if (select(".quill-editor-full")) {
    new Quill(".quill-editor-full", {
      modules: {
        toolbar: [
          [{
            font: []
          }, {
            size: []
          }],
          ["bold", "italic", "underline", "strike"],
          [{
            color: []
          },
          {
            background: []
          }
          ],
          [{
            script: "super"
          },
          {
            script: "sub"
          }
          ],
          [{
            list: "ordered"
          },
          {
            list: "bullet"
          },
          {
            indent: "-1"
          },
          {
            indent: "+1"
          }
          ],
          ["direction", {
            align: []
          }],
          ["link", "image", "video"],
          ["clean"]
        ]
      },
      theme: "snow"
    });
  }

  /**
   * Initiate Bootstrap validation check
   */
  const needsValidation = document.querySelectorAll(".needs-validation")

  Array.prototype.slice.call(needsValidation)
    .forEach((form) => {
      form.addEventListener("submit", (event) => {
        if (!form.checkValidity()) {
          event.preventDefault()
          event.stopPropagation()
        }

        form.classList.add("was-validated")
      }, false)
    })

  /**
   * Initiate Datatables
   */
  const datatables = select(".datatable", true)
  datatables.forEach(datatable => {
    new simpleDatatables.DataTable(datatable);
  })

  /**
   * Autoresize echart charts
   */
  const mainContainer = select("#main");
  if (mainContainer) {
    setTimeout(() => {
      new ResizeObserver(() => {
        select(".echart", true).forEach(getEchart => {
          echarts.getInstanceByDom(getEchart).resize();
        })
      }).observe(mainContainer);
    }, 200);
  }

  /**
   * Avoid hide dropdown when user clicked inside
   */
  const dropdownLotSelector = document.getElementById("dropDownLotsSelector")
  if (dropdownLotSelector != null) { // If exists selector it will set click event
    dropdownLotSelector.addEventListener("click", event => {
      event.stopPropagation();
    })
  }


  /**
   * Search form functionality
   */
  window.addEventListener("DOMContentLoaded", () => {
    const searchForm = document.getElementById("SearchForm")
    const inputSearch = document.querySelector("#SearchForm > input")
    const doSearch = true

    searchForm.addEventListener("submit", (event) => {
      event.preventDefault();
    })

    let timeoutHandler = setTimeout(() => { }, 1)
    const dropdownList = document.getElementById("dropdown-search-list")
    const defaultEmptySearch = document.getElementById("dropdown-search-list").innerHTML


    inputSearch.addEventListener("input", (e) => {
      clearTimeout(timeoutHandler)
      const searchText = e.target.value
      if (searchText == "") {
        document.getElementById("dropdown-search-list").innerHTML = defaultEmptySearch;
        return
      }

      let resultCount = 0;
      function searchCompleted() {
        resultCount++;
        setTimeout(() => {
          if (resultCount == 2 && document.getElementById("dropdown-search-list").children.length == 2) {
            document.getElementById("dropdown-search-list").innerHTML = `
            <li id="deviceSearchLoader" class="dropdown-item">
            <i class="bi bi-x-lg"></i>
                    <span style="margin-right: 10px">Nothing found</span>
            </li>`
          }
        }, 100)
      }

      timeoutHandler = setTimeout(async () => {
        dropdownList.innerHTML = `
        <li id="deviceSearchLoader" class="dropdown-item">
            <i class="bi bi-laptop"></i>
            <div class="spinner-border spinner-border-sm" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        </li>
        <li id="lotSearchLoader" class="dropdown-item">
            <i class="bi bi-folder2"></i>
            <div class="spinner-border spinner-border-sm" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        </li>`;


        try {
          Api.search_device(searchText.toUpperCase()).then(devices => {
            dropdownList.querySelector("#deviceSearchLoader").style = "display: none"

            for (let i = 0; i < devices.length; i++) {
              const device = devices[i];

              // See: ereuse_devicehub/resources/device/models.py
              const verboseName = `${device.type} ${device.manufacturer} ${device.model}`

              const templateString = `
              <li>
                  <a class="dropdown-item" href="${API_URLS.devices_detail.replace("ReplaceTEXT", device.devicehubID)}" style="display: flex; align-items: center;" href="#">
                      <i class="bi bi-laptop"></i>
                      <span style="margin-right: 10px">${verboseName}</span>
                      <span class="badge bg-secondary" style="margin-left: auto;">${device.devicehubID}</span>
                  </a>
              </li>`;
              dropdownList.innerHTML += templateString
              if (i == 4) { // Limit to 4 resullts
                break;
              }
            }

            searchCompleted();
          })
        } catch (error) {
          dropdownList.innerHTML += `
          <li id="deviceSearchLoader" class="dropdown-item">
          <i class="bi bi-x"></i>
              <div class="spinner-border spinner-border-sm" role="status">
                  <span class="visually-hidden">Error searching devices</span>
              </div>
          </li>`;
          console.log(error);
        }

        try {
          Api.get_lots().then(lots => {
            dropdownList.querySelector("#lotSearchLoader").style = "display: none"
            for (let i = 0; i < lots.length; i++) {
              const lot = lots[i];
              if (lot.name.toUpperCase().includes(searchText.toUpperCase())) {
                const templateString = `
                <li>
                    <a class="dropdown-item" href="${API_URLS.lots_detail.replace("ReplaceTEXT", lot.id)}" style="display: flex; align-items: center;" href="#">
                        <i class="bi bi-folder2"></i>
                        <span style="margin-right: 10px">${lot.name}</span>
                    </a>
                </li>`;
                dropdownList.innerHTML += templateString
                if (i == 4) { // Limit to 4 resullts
                  break;
                }
              }
            }
            searchCompleted();
          })

        } catch (error) {
          dropdownList.innerHTML += `
          <li id="deviceSearchLoader" class="dropdown-item">
          <i class="bi bi-x"></i>
              <div class="spinner-border spinner-border-sm" role="status">
                  <span class="visually-hidden">Error searching lots</span>
              </div>
          </li>`;
          console.log(error);
        }
      }, 1000)
    })
  })

})();
