import logoImage from "../assets/ekvayu_logo.png";

function Footer() {
  return (
    <footer className="w-full py-4 mt-8 border-t border-border bg-card/20 backdrop-blur-xs text-xs text-muted-foreground/60 transition-colors">
      <div className="flex flex-col sm:flex-row items-center justify-between gap-2 max-w-7xl mx-auto px-4">
        <p className="font-medium">
          &copy; {new Date().getFullYear()} VORA. All rights reserved.
        </p>
        <div className="flex items-center gap-1.5 font-medium">
          <span>Powered by</span>
          <a
            href="https://www.ekvayu.com"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 font-extrabold text-primary/70 hover:text-primary transition-all tracking-wide"
          >
            <img
              src={logoImage}
              alt="Ekvayu Logo"
              className="h-4.5 w-4.5 object-contain inline-block"
              loading="lazy"
              decoding="async"
            />
            <span>Ekvayu Tech Pvt. Ltd.</span>
          </a>
        </div>
      </div>
    </footer>
  );
}

export default Footer;
