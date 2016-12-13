function scrollToBottom() {
    // Autoscroll down to reply button, and then go a little further to
    // account for iPhone's bottom toolbar
    window.scrollTo(0, $("#reply").offset().top - $(window).height() + 50);
}


var grabInFlight  = false;


function grabNewChannelContent(urlTemplate, afterReplaceStr, shouldScrollToBottom) {
	if (grabInFlight) {
		return;
	}
	grabInFlight = true;

	var after = $(".content-table tr:last").attr('id').replace('line-', '');
	$.ajax({
		url: urlTemplate.replace(afterReplaceStr, after),
		cache: false
	}).done(function(html) {
		$(".content-table tr:last").after(html)
		// Scrolling to bottom when new lines are received would be
		// annoying when you're looking at earlier lines; however, we want
		// to scroll to the bottom when we submit a reply.
		if (shouldScrollToBottom) {
			scrollToBottom();
		}
	}).always(function () {
		grabInFlight = false;
	});
}


function pollForNewChannelContent(urlTemplate, afterReplaceStr, interval) {
    setInterval(function() {
		grabNewChannelContent(urlTemplate, afterReplaceStr, false);
    }, interval);
}


function resizeVideoIframes(videoMaxWidth, videoMaxHeight) {
    var contentWidth = $(".content-col").width();
    $("iframe").each(function(elem) {
        contentWidth = (contentWidth > videoMaxWidth) ? videoMaxWidth : contentWidth;
        var aspect = videoMaxWidth / videoMaxHeight;
        $(this).width(contentWidth);
        $(this).height(contentWidth / aspect);
    });
}

function submitReplyAjax(submitUrl, grabUrlTemplate, afterReplaceStr) {
	$("#reply-form").submit(function(e) {
		$.ajax({
			type: "POST",
			url: submitUrl,
			data: $("#reply-form").serialize(), // serializes the form's elements.
			success: function(data) {
				$("#reply-form")[0].reset();
				grabNewChannelContent(grabUrlTemplate, afterReplaceStr, true);
			}
		});
		e.preventDefault(); // avoid to execute the actual submit of the form.
	});
}
