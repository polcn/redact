const puppeteer = require('puppeteer');

// Test credentials
const TEST_EMAIL = 'test.patterns@gmail.com';
const TEST_PASSWORD = 'TestPatterns123!';

async function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function testPatternCheckboxes() {
  console.log('Starting Pattern Checkbox Test...');
  
  const browser = await puppeteer.launch({ 
    headless: false,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  
  try {
    const page = await browser.newPage();
    await page.setViewport({ width: 1280, height: 800 });
    
    // Navigate to the app
    console.log('Navigating to https://redact.9thcube.com...');
    await page.goto('https://redact.9thcube.com', { waitUntil: 'networkidle2' });
    
    // Check if we need to login or sign up
    const loginButton = await page.$('button:contains("Sign In")');
    if (loginButton) {
      console.log('Need to authenticate...');
      
      // Try to sign up first
      const signUpLink = await page.$('a[href="/signup"]');
      if (signUpLink) {
        await signUpLink.click();
        await page.waitForNavigation();
        
        // Fill signup form
        await page.type('input[type="email"]', TEST_EMAIL);
        await page.type('input[type="password"]', TEST_PASSWORD);
        await page.click('button[type="submit"]');
        
        await delay(2000);
      }
    }
    
    // Wait for home page to load
    await page.waitForSelector('h2:contains("Redaction Rules")', { timeout: 10000 });
    console.log('Configuration section loaded!');
    
    // Test each pattern checkbox
    const patterns = [
      { name: 'ssn', label: 'Social Security Numbers' },
      { name: 'credit_card', label: 'Credit Card Numbers' },
      { name: 'phone', label: 'Phone Numbers' },
      { name: 'email', label: 'Email Addresses' },
      { name: 'ip_address', label: 'IP Addresses' },
      { name: 'drivers_license', label: "Driver's License Numbers" }
    ];
    
    console.log('\\nTesting pattern checkboxes...');
    
    for (const pattern of patterns) {
      // Find the checkbox by its label text
      const checkbox = await page.evaluateHandle((labelText) => {
        const labels = Array.from(document.querySelectorAll('label'));
        const label = labels.find(l => l.textContent.includes(labelText));
        return label ? label.querySelector('input[type="checkbox"]') : null;
      }, pattern.label);
      
      if (checkbox) {
        // Get initial state
        const initialState = await page.evaluate(el => el.checked, checkbox);
        console.log(`${pattern.label}: Initially ${initialState ? 'checked' : 'unchecked'}`);
        
        // Click to toggle
        await checkbox.click();
        await delay(500);
        
        // Verify state changed
        const newState = await page.evaluate(el => el.checked, checkbox);
        console.log(`  After click: ${newState ? 'checked' : 'unchecked'}`);
        
        if (initialState === newState) {
          console.error(`  ❌ ERROR: Checkbox state did not change!`);
        } else {
          console.log(`  ✅ Checkbox toggle working`);
        }
      } else {
        console.error(`❌ Could not find checkbox for ${pattern.label}`);
      }
    }
    
    // Test save functionality
    console.log('\\nTesting save configuration...');
    const saveButton = await page.$('button:contains("Save Configuration")');
    if (saveButton) {
      await saveButton.click();
      await delay(2000);
      
      // Check for success message
      const successMessage = await page.$('div:contains("Configuration saved successfully")');
      if (successMessage) {
        console.log('✅ Configuration saved successfully!');
      } else {
        console.log('⚠️  No success message found');
      }
    }
    
    // Reload page and verify persistence
    console.log('\\nReloading page to test persistence...');
    await page.reload({ waitUntil: 'networkidle2' });
    await page.waitForSelector('h2:contains("Redaction Rules")', { timeout: 10000 });
    
    // Check if checkboxes maintained their state
    for (const pattern of patterns) {
      const checkbox = await page.evaluateHandle((labelText) => {
        const labels = Array.from(document.querySelectorAll('label'));
        const label = labels.find(l => l.textContent.includes(labelText));
        return label ? label.querySelector('input[type="checkbox"]') : null;
      }, pattern.label);
      
      if (checkbox) {
        const isChecked = await page.evaluate(el => el.checked, checkbox);
        console.log(`${pattern.label}: ${isChecked ? 'checked' : 'unchecked'} after reload`);
      }
    }
    
    console.log('\\n✅ Test completed!');
    
  } catch (error) {
    console.error('\\n❌ Test failed with error:', error.message);
  } finally {
    await browser.close();
  }
}

// Run the test
testPatternCheckboxes().catch(console.error);