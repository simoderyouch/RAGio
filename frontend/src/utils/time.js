export function time(timestampStr){
    const timestamp = new Date(timestampStr);

    // Extract the time component
    let hours = timestamp.getHours();
    const minutes = timestamp.getMinutes();
    const amPm = hours >= 12 ? 'PM' : 'AM'; // Determine if it's AM or PM
    hours %= 12; // Convert to 12-hour format
    hours = hours || 12; // Handle midnight (0 hours)
   
    // Format minutes with leading zero if needed
    const formattedMinutes = minutes.toString().padStart(2, '0');
    
    return `${hours}:${formattedMinutes} ${amPm}`;
}
