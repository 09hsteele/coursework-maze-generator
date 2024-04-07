function validate_username(username) {
    const allowed_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-_"
    for (const c of $("#username").val()) {
        if (!allowed_chars.includes(c)) {
            toast_message("Username can only contain letters, numbers, full stops, hyphens and underscores", "error")
            return false;
        }
    }
    return true;
}