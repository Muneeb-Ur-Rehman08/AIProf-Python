/*===================================================
Project: AI2BC SmartLet Property Managament
====================================================*/

//GLOBAL VARIBALES

//selector constants
var root = $("html, body");
const main_window = $(window),
  pageBody = $("body"),
  bdyOnePage = $("body.landing-page-demo "),
  hasSubMenu = $(".has-sub-menu"),
  pageHeader = $("#page-header"),
  navMain = $("#main-nav"),
  toTopBtn = $(".back-to-top"),
  heroVegasSlider = $(".page-hero.hero-vegas-slider"),
  textInput = $("form.main-form .text-input"),
  tabLink = $(".ma-tabs .tabs-links .tab-link");
  // portfolioGroup = $(".portfolio .portfolio-group");

$(function () {
  ("use strict");

  // function to fire the conter plugin
  let counterShowsUp = false;

  function fireCounter() {
    if ($(".js-stats-counter").length) {
      if (jQuery().countTo && counterShowsUp === false) {
        let pos = $(".js-stats-counter").offset().top;
        if (main_window.scrollTop() + main_window.innerHeight() - 50 >= pos) {
          $(".counter").countTo();
          counterShowsUp = true;
        }
      }
    }
  }

  // Start open/close navbar search box
  // $(".header-search-box form").on("click", function (e) {
  //   e.stopPropagation();
  // });

  // $(".header-search-btn").on("click", function () {
  //   $(".header-search-box").addClass("show");

  //   setTimeout(function () {
  //     $(".search-input").focus();
  //   }, 1000);
  // });

  /* ********* Start dark mode switcher ***********/

  // const modeSwitcher = $(".mode-switcher");
  const themeStoredKey = "ThemeColor";
  const darkTheme_class = "dark-theme";
  // const lightTheme_class = "light-theme";
  const themeStoredItem = localStorage.getItem(themeStoredKey);

  /*********  Custom functions Area *********/

   function setThemeMode(themeColor) {
     if (themeColor !== darkTheme_class) {
       pageBody.addClass(darkTheme_class);
      //  modeSwitcher.addClass(darkTheme_class).removeClass(lightTheme_class);
       localStorage.setItem(themeStoredKey, darkTheme_class);
       localStorage.removeItem(lightTheme_class);
     }
   }

  /* *******  Set the theme according to the local storage value ********/
   //if local storge not set or the body has class value of .dark-theme THEN default theme is dark
   if (!themeStoredItem && !pageBody.hasClass(darkTheme_class)) {
     setThemeMode(darkTheme_class);
   }
  // the only case to be light mode is when the local storge has he value of light-theme
  // if (themeStoredItem === lightTheme_class) {
  //   setThemeMode(lightTheme_class);
  // }

  // if local storge or the body has class value of .dark-theme
  if (
    themeStoredItem === darkTheme_class ||
    pageBody.hasClass(darkTheme_class)
  ) {
    setThemeMode(darkTheme_class);
  }

  // /* ******* Set the theme by clicking the theme switcher ********/
  // $(modeSwitcher).on("click", function () {
  //   if ($(this).is("." + darkTheme_class)) {
  //     setThemeMode(lightTheme_class);
  //   } else if ($(this).is("." + lightTheme_class)) {
  //     setThemeMode(darkTheme_class);
  //   }
  // });

  /********************************
   *  START #page-header js rules
   *********************************/

  /* *******  start open/close navbar search box   ********/
  // $(".header-search-box .close-search , .header-search-box").on("click", () => {
  //   $(".header-search-box").removeClass("show");
  // });

  if (navMain) {
    // Check if scrollspy is defined before using it
    if ($.fn.scrollspy) {
      $(bdyOnePage).scrollspy({
        target: navMain,
        offset: navMain.innerHeight() + 1,
      });
    } else {
      console.error("scrollspy is not a function. Please ensure the Bootstrap JS is included.");
    }
  }

  // make the menu stick on top whlie reloading

  console.log($(this).scrollTop());
  
  if ($(this).scrollTop() > 50) {
    if (!$(pageHeader).hasClass("is-sticky")) {
      pageHeader.addClass("is-sticky");
    }
  }

  /* *******  make the menu stick on top upon the page scrolling   ********/
  main_window.on("scroll", function () {
    if ($(this).scrollTop() > 50) {
      if (!$(pageHeader).hasClass("is-sticky")) {
        pageHeader.addClass("is-sticky");
      }
    } else {
      if ($(pageHeader).hasClass("is-sticky")) {
        pageHeader.removeClass("is-sticky");
      }
    }
  });

  /* *******  show/hide navbar links menu  ********/
  $(".menu-toggler").on("click", function () {
    pageHeader.find(".show:not(.menu-wrapper) ").removeClass("show");
    pageHeader.find(".menu-wrapper").toggleClass("show");
    $(".menu-toggler").toggleClass("close-menu");
  });

  /* ******* close the currnt opend menu when click on its wrapper ********/
  $(".links-list").on("click", function (e) {
    e.stopPropagation();
  });

  $(".menu-wrapper").on("click", function () {
    $(this).removeClass("show");
    if ($(".menu-toggler").hasClass("close-menu")) {
      $(".menu-toggler").removeClass("close-menu");
    }
  });

  /* ******* showing navbar sub-menus on mobile ********/
  hasSubMenu.on("click", function (e) {
    e.stopPropagation();
    if (!(main_window.innerWidth() > 1199)) {
      $(this).children(".sub-menu").slideToggle();
    }
  });

  /* ******* Start Smooth Scrolling To page sections Area********/
  $(".landing-page-demo .menu-navbar .menu-link").on("click", function (e) {
    const link = $(this).attr("href");
    let currentMainNavHeight = navMain.innerHeight();
    if (link.charAt(0) === "#") {
      e.preventDefault();
      const target = this.hash;
      $(root).animate(
        {
          scrollTop: $(target).offset().top - currentMainNavHeight + 1,
        },
        500
      );

      if (!$(this).parent(".menu-item").hasClass("has-sub-menu")) {
        // to close the menu after going to crossponding section
        if ($(".menu-wrapper").hasClass("show")) {
          $(".menu-wrapper").removeClass("show");
        }

        // to change the menu toggler buttn icon
        if ($(".menu-toggler").hasClass("close-menu")) {
          $(".menu-toggler").removeClass("close-menu");
        }
      }
    }
  });

  /*********************************
   END #page-header js rules
  *********************************/
  if ($(textInput).length) {
    let inputHasText = "has-text";

    if ($(textInput).val().trim() !== "")
      $(textInput).parent().addClass(inputHasText);
    else $(textInput).parent().removeClass(inputHasText);

    /*
        check if the form input has data or not while focusing out
        from the input to set the label
        in the right place by the css rules.
        */
    $(textInput).on("focusout", function () {
      if ($(this).val().trim() !== "") {
        $(this).parent().addClass(inputHasText);
      } else {
        $(this).parent().removeClass(inputHasText);
      }
    });
  }

  // Start Smooth Scrolling To Window Top When Clicking on Back To Top Button
  $(toTopBtn).on("click", function () {
    root.css("scroll-behavior", "smooth").scrollTop(0);
  });
  // End Smooth Scrolling To Window Top When Clicking on Back To Top Button

  /* Start Portfolio btns  */
  // if ($(".portfolio .portfolio-btn").length) {
  //   $(".portfolio .portfolio-btn").on("click", function () {
  //     $(this).addClass("active").siblings().removeClass("active");

  //     const $filterValue = $(this).attr("data-filter");
  //     portfolioGroup.isotope({
  //       filter: $filterValue,
  //     });
  //   });
  // }

  /* *******   initialize Counter plugin ********/
   fireCounter();

  /* ********* set the Background Image path and opacity for elements that has the  a vlaue for data-bg-img attribute***********/
  const bg_img = $("*");
  bg_img.each(function () {
    if ($(this).attr("data-bg-img")) {
      $(this).css("background-image", `url(${$(this).attr("data-bg-img")}`);
    }
    if ($(this).attr("data-bg-opacity")) {
      $(this).css("opacity", `${$(this).attr("data-bg-opacity")}`);
    }
  });

  /* *******  Start skills Bars  ********/
  $(window).on("scroll", function () {
    $(".skills .skill .skill-bar .bar").each(function () {
      let barOriginalPosition = $(this).offset().top + $(this).outerHeight();
      let barCurrPosition = $(window).scrollTop() + $(window).height();
      let widthValue = $(this).attr("data-skill-val");
      if (barCurrPosition > barOriginalPosition) {
        $(this).css({
          width: widthValue + "%",
        });
      }
    });
  });

  /* ******* Start Percentage loading screen interactions ********/
  // let percentage = 0;
  // let LoadingCounter = setInterval(function () {
  //   if (percentage <= 100) {
  //     // $('#loading-screen ').css('opacity', (100 - percentage));
  //     $("#loading-screen .loading-counter").text(percentage + "%");
  //     $("#loading-screen .bar").css("width", (100 - percentage) / 2 + "%");
  //     $("#loading-screen .progress-line").css(
  //       "transform",
  //       "scale(" + percentage / 100 + ")"
  //     );
  //     percentage++;
  //   } else {
  //     $("#loading-screen").fadeOut(500);
  //     setTimeout(() => {
  //       $("#loading-screen").remove();
  //     }, 1500);
  //     clearInterval(LoadingCounter);
  //   }
  // }, 10);

   main_window.on("scroll", function () {
     if ($(this).scrollTop() > 50) {
       //show back to top btn
       toTopBtn.addClass("show");
     } else {
       //hide back to top btn
       toTopBtn.removeClass("show");
     }
    
    // to make sure the counter will start counting while its section apear on the screen
     fireCounter();
   });

  /*************Start Contact Form Functionality************/

  const contactForm = $("#contact-us-form"),
    userName = $("#user-name"),
    userEmail = $("#user-email"),
    msgSubject = $("#msg-subject"),
    msgText = $("#msg-text"),
    submitBtn = $("#submit-btn");

  let isValidInput = false,
    isValidEmail = false;

  function ValidateNotEmptyInput(input, errMsg) {
    if (input.length) {
      if (input.val().trim() === "") {
        $(input).siblings(".error-msg").text(errMsg).css("display", "block");
        isValidInput = false;
      } else {
        $(input).siblings(".error-msg").text("").css("display", "none");
        isValidInput = true;
      }
    }
  }

  function validateEmailInput(emailInput) {
    let pattern =
      /^(([^<>()\[\]\\.,;:\s@"]+(\.[^<>()\[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;

    if (pattern.test(emailInput.val()) === false) {
      $(emailInput)
        .siblings(".error-msg")
        .text("Please Enter a valid Email")
        .css("display", "block");
      isValidEmail = false;
    } else {
      $(emailInput).siblings(".error-msg").text("").css("display", "none");
      isValidEmail = true;
    }
  }

  submitBtn.on("click", function (e) {
    e.preventDefault();

    ValidateNotEmptyInput(userName, "Please Enter Your Name");
    ValidateNotEmptyInput(userEmail, "Please Enter Your Email");
    ValidateNotEmptyInput(msgSubject, "Please Enter Your subject");
    ValidateNotEmptyInput(msgText, "Please Enter Your Message");
    validateEmailInput(userEmail);

    if (isValidInput && isValidEmail) {
      $.ajax({
        type: "POST",
        url: contactForm.attr("action"),
        data: contactForm.serialize(),

        success: function (data) {
          $(".done-msg")
            .text("Thank you, Your Message Was Received!")
            .toggleClass("show");
          setTimeout(function () {
            $(".done-msg").text("").toggleClass("show");
          }, 3000);
          contactForm[0].reset();
        },
      });
      return false;
    }
  });

  /*************End Contact Form Functionality************/

  /* ********************************
    Start Vendors plugins options Area 
    *********************************/

  //initialize swiper [Hero Section] //fade slider
  if ($(".hero-swiper-slider.fade-effect .swiper-container").length) {
    const heroSlider = new Swiper(
      ".hero-swiper-slider.fade-effect .swiper-container",
      {
        speed: 1000,
        loop: true,
        reverseDirection: true,
        effect: "fade",
        fadeEffect: {
          crossFade: true,
        },
        on: {
          init: function () {
            let thisSlider = this;
            $(".slides-count").html("0" + (this.slides.length - 2));
            $(".curent-slide").html("0" + (this.realIndex + 1));
          },
          slideChange: function () {
            $(".curent-slide").html("0" + (this.realIndex + 1));
          },
        },
        autoplay: {
          delay: 5000,
          disableOnInteraction: true,
        },
        pagination: {
          el: ".hero-swiper-slider.fade-effect .swiper-pagination",
          type: "bullets",
          clickable: true,
        },
        navigation: {
          nextEl: ".hero-swiper-slider.fade-effect .swiper-button-next",
          prevEl: ".hero-swiper-slider.fade-effect .swiper-button-prev",
        },
      }
    );
  }
  if ($(".hero-swiper-slider.slide-effect .swiper-container").length) {
    const heroSlider = new Swiper(
      ".hero-swiper-slider.slide-effect .swiper-container",
      {
        speed: 1000,
        loop: true,
        reverseDirection: true,
        effect: "slide",
        fadeEffect: {
          crossFade: true,
        },
        on: {
          init: function () {
            let thisSlider = this;
            $(".slides-count").html("0" + (this.slides.length - 2));
            $(".curent-slide").html("0" + (this.realIndex + 1));
          },
          slideChange: function () {
            $(".curent-slide").html("0" + (this.realIndex + 1));
          },
        },
        autoplay: {
          delay: 5000,
          disableOnInteraction: true,
        },
        pagination: {
          el: ".hero-swiper-slider.slide-effect .swiper-pagination",
          type: "bullets",
          clickable: true,
        },
        navigation: {
          nextEl: ".hero-swiper-slider.slide-effect .swiper-button-next",
          prevEl: ".hero-swiper-slider.slide-effect .swiper-button-prev",
        },
      }
    );
  }

  // initialize swiper [Testimonials with 1 Column]
  if ($(".testimonials-1-col  .swiper-container").length) {
    const testimonialsSlider_1 = new Swiper(
      ".testimonials-1-col  .swiper-container",
      {
        // Optional parameters
        speed: 500,
        loop: true,
        grabCursor: true,
        slidesPerView: 1,
        spaceBetween: 50,
        delay: 5000,
        autoplay: {
          delay: 5000,
        },
        navigation: {
          nextEl: ".testimonials-1-col .swiper-button-next",
          prevEl: ".testimonials-1-col .swiper-button-prev",
        },
        on: {
          resize: function () {
            this.update();
          },
        },
      }
    );
  }

  //initialize swiper [clients Section]
  if ($(".our-clients .swiper-container").length) {
    const partenersSlider = new Swiper(".our-clients .swiper-container", {
      // Optional parameters
      speed: 600,
      loop: true,
      spaceBetween: 20,
      grabCursor: true,
      delay: 5000,
      autoplay: {
        delay: 5000,
      },
      slidesPerView: 3,
      breakpoints: {
        991: {
          slidesPerView: 6,
          spaceBetween: 30,
        },
      },
    });
  }

  //initialize swiper [portfolio-slider]
  // if ($(".portfolio-slider .swiper-container").length) {
  //   const swiperPortfolioSlider = new Swiper(
  //     ".portfolio-slider .swiper-container",
  //     {
  //       speed: 600,
  //       loop: true,
  //       centeredSlides: true,
  //       slidesPerView: 1,
  //       spaceBetween: 30,
  //       autoplay: {
  //         delay: 5000,
  //       },
  //       breakpoints: {
  //         991: {
  //           slidesPerView: 2,
  //           spaceBetween: 30,
  //         },
  //       },
  //       navigation: {
  //         nextEl: ".portfolio-slider .swiper-button-next",
  //         prevEl: ".portfolio-slider .swiper-button-prev",
  //       },
  //     }
  //   );
  // }

  //initialize swiper [portfolio-single]
  // if (
  //   $(".portfolio-single .portfolio-single-slider .swiper-container").length
  // ) {
  //   const swiperPortfolioSingleSlider = new Swiper(
  //     ".portfolio-single .portfolio-single-slider .swiper-container",
  //     {
  //       spaceBetween: 10,
  //       grabCursor: true,
  //       reverseDirection: true,
  //       loop: true,
  //       slidesPerView: 1,
  //       autoplay: {
  //         delay: 5000,
  //         disableOnInteraction: true,
  //       },

  //       navigation: {
  //         nextEl: ".portfolio-single-slider .swiper-button-next",
  //         prevEl: ".portfolio-single-slider .swiper-button-prev",
  //       },
  //     }
  //   );
  // }

  /* *******  loading  wow.js  Options ********/
  const wow = new WOW({
    animateClass: "animated",
    offset: 100,
  });
  wow.init();

  /* *******  loading fancybox.js library ********/
  if ($("*").fancybox) {
    $().fancybox({
      selector: '[data-fancybox=".show-in-fancybox "]:visible',
      loop: true,
      buttons: ["zoom", "close"],
    });
  }

  /* *******  loading tilt.js library ********/
  // if (jQuery().tilt) {
  //   $("[data-tilt]").tilt({
  //     perspective: 1000,
  //   });
  // }

  /* *******  Loading the isotope plugin ********/
  // if (jQuery().isotope) {
  //   portfolioGroup.isotope({
  //     // options
  //     itemSelector: ".portfolio-item",
  //     layoutMode: "fitRows",
  //     percentPosition: true,
  //     filter: "*",
  //     stagger: 30,
  //     containerStyle: null,
  //   });
  // }

  /* *******  Start particles.js ********/
  if ($(".particles-js.dots").length) {
    // constant to hold the particals options
    const customParticlesOptions = {
      particles: {
        number: {
          value: 150,
          density: {
            enable: true,
            value_area: 500,
          },
        },
        color: {
          value: "#09aff4",
        },
        shape: {
          type: "circle",
          stroke: {
            width: 0,
            color: "#000000",
          },
          polygon: {
            nb_sides: 5,
          },
          image: {
            src: "img/github.svg",
            width: 100,
            height: 100,
          },
        },
        opacity: {
          value: 0.5,
          random: true,
          anim: {
            enable: true,
            speed: 1,
            opacity_min: 0,
            sync: false,
          },
        },
        size: {
          value: 3,
          random: true,
          anim: {
            enable: true,
            speed: 5,
            size_min: 0.3,
            sync: false,
          },
        },
        line_linked: {
          enable: false,
          distance: 150,
          color: "#ffffff",
          opacity: 0.4,
          width: 1,
        },
        move: {
          enable: true,
          speed: 5,
          direction: "none",
          random: true,
          straight: false,
          out_mode: "out",
          bounce: false,
          attract: {
            enable: false,
            rotateX: 600,
            rotateY: 1200,
          },
        },
      },
      interactivity: {
        detect_on: "canvas",
        events: {
          onhover: {
            enable: false,
            mode: "bubble",
          },
          onclick: {
            enable: false,
            mode: "repulse",
          },
          resize: true,
        },
        modes: {
          grab: {
            distance: 400,
            line_linked: {
              opacity: 1,
            },
          },
          bubble: {
            distance: 250,
            size: 0,
            duration: 2,
            opacity: 0,
            speed: 3,
          },
          repulse: {
            distance: 400,
            duration: 0.4,
          },
          push: {
            particles_nb: 4,
          },
          remove: {
            particles_nb: 2,
          },
        },
      },
      retina_detect: true,
    };
    particlesJS("particles-js", customParticlesOptions);
  }

  /* *******  loading Splitting.js library ********/
  if (!(typeof window.Splitting === "undefined")) {
    if ($("[data-splitting]").length) {
      Splitting();
    }
  }

  /* *******  loading simpleParallax.js library ********/
  if (!(typeof window.simpleParallax === "undefined")) {
    let parallaxblock = document.querySelectorAll(".parallax-img ");
    if (parallaxblock.length) {
      new simpleParallax(parallaxblock, {
        delay: 1,
      });
      
    }
  }
  /************************************
    End Vendors plugins options Area 
     ******************************** */
});

/***************** social media post redirect ********************/

  // Add an event listener when user clicks navbar facebook link and prevent default 
  document.getElementById('facebookShareLink').addEventListener('click', function (e) {
    e.preventDefault();
    // call the function that will redirect the users to share to their facebook
    shareOnFacebook();
  });

  function shareOnFacebook() {
    // Set website url to be shared and Message
    var urlToShare = 'https://meetyourai.github.io/AIProf/';
    var shareMessage = 'Check out this amazing website! Learning made easy with Artificial Intelligence';

    // Construct the Facebook share URL
    var facebookShareUrl = 'https://www.facebook.com/sharer/sharer.php?u=' + encodeURIComponent(urlToShare) + '&quote=' + encodeURIComponent(shareMessage);

    // Open the Facebook share dialog in a new window
    window.open(facebookShareUrl, 'Share on Facebook', 'width=600,height=400');
  }

  // Add an event listener when user clicks Twitter/X link and prevent default
  document.getElementById('twitterShareLink').addEventListener('click', function (e) {
    e.preventDefault();
    // call the function that will redirect the users to share to their Twitter Profile
    shareOnTwitter();
  });

  function shareOnTwitter() {
    // Set website url to be shared and Message
    var urlToShare = 'https://meetyourai.github.io/AIProf/';
    var tweetMessage = 'Check out this awesome website! Learning made easy with Artificial Intelligence';

    // Construct the Twitter share URL
    var twitterShareUrl = 'https://twitter.com/intent/tweet?url=' + encodeURIComponent(urlToShare) + '&text=' + encodeURIComponent(tweetMessage);

    // Open the Twitter share dialog in a new window
    window.open(twitterShareUrl, 'Share on Twitter', 'width=600,height=400');
  }

  // Add an event listener when user clicks Whatsapp icon link and prevent default
  document.getElementById('whatsappShareLink').addEventListener('click', function (e) {
    e.preventDefault();
    // call the function that will redirect the users to share to their Twitter Profile
    shareOnWhatsApp();
  });

  function shareOnWhatsApp() {
    // Set website url to be shared and Message
    var urlToShare = 'https://meetyourai.github.io/AIProf/';
    var message = 'Learning made easy with AI: Check out this website: ' + urlToShare;

    // Create a WhatsApp share link
    var whatsappShareUrl = 'https://api.whatsapp.com/send?text=' + encodeURIComponent(message);

    // Redirect the user to the WhatsApp share link
    window.location.href = whatsappShareUrl;
  }

  // event listener for paypal button click to alert user its coming soon
  document.getElementById('paypal-button').addEventListener('click', function (e) {
    e.preventDefault();
    // call the function that will redirect the users to share to their Twitter Profile
    alert("Paypal subscription is coming soon!");
  });

	/* for paypal integration
	<script src="https://www.paypal.com/sdk/js?client-id=YOUR_CLIENT_ID&vault=true&intent=subscription">
	</script> Add your client_id */

/* script start demo for paypal subscription button
 <script>
		paypal.Buttons({
		 createSubscription: function(data, actions) {
		   return actions.subscription.create({
			'plan_id': 'YOUR_PLAN_ID' // Creates the subscription
			});
		  },
		  onApprove: function(data, actions) {
			alert('You have successfully subscribed to ' + data.subscriptionID); // Optional message given to subscriber
		  }
		}).render('#paypal-button-container'); // Renders the PayPal button
	   </script> -->
	<!-- paypal dev docs: https://developer.paypal.com/docs/subscriptions/integrate/ */
