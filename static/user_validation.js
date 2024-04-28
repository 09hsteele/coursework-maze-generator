function validate_username(username) {
    const allowed_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-_"
    for (const c of username) {
        if (!allowed_chars.includes(c)) {
            toast_message("Username can only contain letters, numbers, full stops, hyphens and underscores", "error")
            return false;
        }
    }
    return true;
}

function validate_password(password) {
    if (password.length < 8) {
        toast_message("Password must be 8 or more characters long", "error");
        return false;
    }
    if (password === password.toLowerCase()) {
        // if password == lowercase password then all alphabetic characters must already be lowercase
        toast_message("Password must include at least one capital letter", "error");
        return false;
    }
    if (password === password.toUpperCase()) {
        // if password == uppercase password then all alphabetic characters must already be uppercase
        toast_message("Password must include at least one lowercase letter", "error");
        return false;
    }
    if (!/\d/.test(password)) {
        //  /\d/ matches any digit. This will run whenever there are no matches
        toast_message("Password must include at least one number", "error");
        return false;
    }
    return true;
}
