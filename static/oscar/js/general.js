$(function(){

  var $container = $('#grid-masonry'),
      $checkboxes = $('#filters input');

	  
	  
  $container.imagesLoaded(function()
  {
	$container.isotope({
    itemSelector: '.grid-item'
	});
  });
  

  // get Isotope instance
  var isotope = $container.data('isotope');
  // add even classes to every other visible item, in current order
  function addEvenClasses() {
    isotope.$filteredAtoms.each( function( i, elem ) {
      $(elem)[ ( i % 2 ? 'addClass' : 'removeClass' ) ]('even')
    });
  }

  $checkboxes.change(function(){
    var filters = [];
    // get checked checkboxes values
    $checkboxes.filter(':checked').each(function(){
      filters.push( this.value );
    });
    // ['.red', '.blue'] -> '.red, .blue'
    filters = filters.join(', ');
    $container.isotope({ filter: filters });
    addEvenClasses();
  });

});
/*
var elem = document.querySelector('#grid-masonry');

$('#grid-masonry').imagesLoaded(function()
{
	var msnry = new Masonry (elem, {
		itemSelector: '.grid-item',
	});
});

jQuery.fn.multiselect = function() {
	$(this).each(function() {
        var checkboxes = $(this).find("input:checkbox");
        checkboxes.each(function() {
			var checkbox = $(this);

            checkbox.click(function() {
                var dummy = 0;

				$( ".grid-item" ).hide();
				$(".checkboxall").each(function() {
					$(this).parent().removeClass("multiselect-on");
					
					if(this.checked==true){
							$(this).parent().addClass("multiselect-on");
							dummy=dummy+1;
							var vartag=$(this).val();				

							$( ".grid-item[name*="+vartag+"]" ).show();
							//$( "[class*="vartag"]" ).show();
							//$("."+vartag).show();
					}
				});
				if (dummy == 0){
					$( ".grid-item" ).show();
				}
				
				var container = document.querySelector('#grid-masonry');
				new Masonry( container, {
				//new Masonry (elem, {
						itemSelector: '.grid-item',
					});	
            });
        });
		
    });
};


*/

$(function() {
     $(".parent-multiselect").multiselect();
});

$(function () {
    var sidebar = $('.sidebar');
    var top = sidebar.offset().top - parseFloat(sidebar.css('margin-top'));
  
    $(window).scroll(function (event) {
      var y = $(this).scrollTop();
      if (y >= top) {
        sidebar.addClass('fixed');
      } else {
        sidebar.removeClass('fixed');
      }
    });
});
		
(function () {
    document.getElementById("chkbox-Red").style.background = "#800000"; 
	document.getElementById("chkbox-Black").style.background = "black";
	document.getElementById("chkbox-Green").style.background = "#3cb371";
	document.getElementById("chkbox-Grey").style.background = "grey";
	document.getElementById("chkbox-White").style.background = "white";
	document.getElementById("chkbox-Brown").style.background = "brown";
	document.getElementById("chkbox-Blue").style.background = "#6a5acd";
	document.getElementById("chkbox-Yellow").style.background = "#FFFF99";	
	document.getElementById("chkbox-Purple").style.background = "#800080";
	document.getElementById("chkbox-Pink").style.background = "#FFC0CB";
	document.getElementById("chkbox-Beige").style.background = "#d3d3d3";
	document.getElementById("chkbox-Orange").style.background = "#FF7F50";
})();

$(window).scroll(function() {
    if ($(this).scrollTop() >= 50) {        // If page is scrolled more than 50px
        $('#return-to-top').fadeIn(200);    // Fade in the arrow
    } else {
        $('#return-to-top').fadeOut(200);   // Else fade out the arrow
    }
});
$('#return-to-top').click(function() {      // When arrow is clicked
    $('body,html').animate({
        scrollTop : 0                       // Scroll to top of body
    }, 500);
});



function openNav() {
    document.getElementById("mySidenav").style.display = "block";
	document.getElementById("rightarrow").style.display = "none";
	document.getElementById("leftarrow").style.display = "block";
}

function closeNav() {
    document.getElementById("mySidenav").style.display = "none";
	document.getElementById("rightarrow").style.display = "block";
	document.getElementById("leftarrow").style.display = "none";
}